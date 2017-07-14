import mab
import newsbot
import re
import os
import pickle
import numpy as np
import pandas as pd
import datetime
import uuid
from flask import redirect


class MABSlackNewsBot(object):
    def __init__(self, config_dict):
        self.config_dict = config_dict
        self.config_server = config_dict['SERVER']
        self.config_slack = config_dict['SLACK']
        self.config_content = config_dict['CONTENTS']
        self.config_file = config_dict['FILE']

        # fresh_start = yes, remove all pickle files
        self.fresh_start = True if self.config_server['fresh_start'].upper() in {'YES', 'TRUE'} else False
        file_params = self.config_file['pickle_params']
        file_algorithm = self.config_file['pickle_algorithm']
        file_articles = self.config_file['pickle_articles']
        if self.fresh_start:
            try:
                os.remove(file_params)
                os.remove(file_algorithm)
                os.remove(file_articles)
            except OSError:
                pass

        # load internal parameters
        self.variation_strings = []
        self.num_variations = 0
        self.rewards = None
        if os.path.isfile(file_params):
            self.__pickle_params_load()  # load from pickled file
        else:
            for key_str in self.config_content:
                if 'variation' in key_str:
                    self.variation_strings.append(self.config_content[key_str])
            self.num_variations = len(self.variation_strings)
            self.rewards = [np.array([]) for i in range(self.num_variations)]   # list of empty numpy arrays

        # create a multi-armed bandit algorithm instance, or reload
        self.mab = None
        if os.path.isfile(file_algorithm):
            self.__pickle_algorithm_load()
        else:
            class_ = getattr(mab, self.config_content['mab_algorithm'])
            params = self.config_content['mab_algorithm_params']
            if len(params) > 0:
                params = re.split('[\s,]+', self.config_content['mab_algorithm_params'])
                params = [float(param) for param in params]  # string to text
                self.mab = class_(self.num_variations, *params)
            else:
                self.mab = class_(self.num_variations)

        # load all articles have served
        self.articles = None
        if os.path.isfile(file_articles):
            self.__pickle_articles_load()
        else:
            self.articles = [pd.DataFrame() for i in range(self.num_variations)]  # list of empty pandas data frames

        # news scrapper and slack bot
        self.scrapper = newsbot.NewsScrapperGoogle()
        self.bot = newsbot.SlackNewsBot(self.config_slack)

        # etcs
        self.host = self.config_server['host']
        self.port = int(self.config_server['port'])
        self.server_url = 'http://{}:{}/'.format(self.host, self.port)
        self.message_title = self.config_slack['message_title']
        self.num_news_display = int(self.config_slack['num_news_display'])
        self.recipient = self.config_slack['recipient']
        self.recipient = re.sub(r'//#|\\#', '#', self.recipient)  # remove escape '/' of '/#'
        self.print_variation_info =\
            True if self.config_slack['print_variation_info'].upper() in {'YES', 'TRUE'} else False
        self.shuffle = True if self.config_slack['shuffle'].upper() in {'YES', 'TRUE'} else False
        self.current_arm = None
        self.current_rewards = np.zeros(self.num_variations)
        self.posted = False

    def post_news(self):
        # dump all changing states on the previous post
        if self.posted:
            self.__save_states()

        self.current_arm = self.mab.select_arm()
        selected_variation = self.variation_strings[self.current_arm]
        article_df = self.scrapper.scrap_by_multiple_words(selected_variation)

        # filter out the only unique news that have not been posted before
        new_titles = article_df['title'].values  # output: numpy array
        old_titles = np.array([])
        for i in range(self.num_variations):
            if len(self.articles[i]) != 0:
                old_titles = np.append(old_titles, self.articles[i]['title'].values)
        unique_titles = np.setdiff1d(new_titles, old_titles)
        article_df = article_df[article_df['title'].isin(unique_titles)]  # remove old news
        unique_num_news_display = min(len(article_df), self.num_news_display)
        article_df = article_df.head(unique_num_news_display)  # choose head news

        # randomly shuffle rows: https://stackoverflow.com/questions/29576430/shuffle-dataframe-rows
        if self.shuffle:
            article_df = article_df.sample(frac=1).reset_index(drop=True)

        # generate redirection urls for the news
        redirect_urls = []
        clicks = []
        for idx in range(len(article_df)):
            redirect_urls.append(self.server_url + '{}-'.format(self.current_arm) + str(uuid.uuid4()))
            clicks.append(0)
        article_df['redirect_link'] = redirect_urls
        article_df['clicks'] = clicks

        self.articles[self.current_arm] = self.articles[self.current_arm].append(article_df, ignore_index=True)

        # post news messages to slack
        pref_msg_text = self.message_title
        if self.print_variation_info:
            pref_msg_text += ' ({})'.format(selected_variation)
        msg_text = datetime.datetime.now().strftime('*_{}, %Y/%m/%d %H:%M_*'.format(pref_msg_text))
        self.bot.post_message(self.recipient, article_df, msg_text)
        self.posted = True

    def redirect_handler(self, path):
        arm = int(path.split('-')[0])
        self.current_rewards[arm] += 1
        df = self.articles[arm]
        if len(df):
            match_condition = df['redirect_link'] == self.server_url + path
            matched_df = df[match_condition]
            if len(matched_df) > 0:
                redirection_url = matched_df.iloc[0]['link']
                row_index = df[match_condition].index.values[0]  # row index of the first matched article
                clicks = df[match_condition].iloc[0]['clicks']  # and its cumulative click count
                df.set_value(row_index, 'clicks', clicks + 1)  # update the click count
                return redirect(redirection_url)
        return redirect(self.config_slack['default_redirect_link'])

    def __save_states(self):
        self.rewards[self.current_arm] =\
            np.append(self.rewards[self.current_arm], self.current_rewards[self.current_arm])
        self.mab.update(self.current_arm, self.current_rewards[self.current_arm])  # update algorithm state
        self.current_rewards = np.zeros(self.num_variations)
        self.__pickle_algorithm_dump()
        self.__pickle_params_dump()
        self.__pickle_articles_dump()

    def __pickle_algorithm_dump(self):
        file_algorithm = self.config_file['pickle_algorithm']
        with open(file_algorithm, 'wb') as f:
            pickle.dump(self.mab, f)

    def __pickle_algorithm_load(self):
        file_algorithm = self.config_file['pickle_algorithm']
        with open(file_algorithm, 'rb') as f:
            self.mab = pickle.load(f)

    def __pickle_params_dump(self):
        file_params = self.config_file['pickle_params']
        pickle_pack_dict = {'variation_strings': self.variation_strings,
                            'rewards': self.rewards}
        with open(file_params, 'wb') as f:
            pickle.dump(pickle_pack_dict, f)

    def __pickle_params_load(self):
        file_params = self.config_file['pickle_params']
        with open(file_params, 'rb') as f:
            pickle_pack_dict = pickle.load(f)
        self.variation_strings = pickle_pack_dict['variation_strings']
        self.num_variations = len(self.variation_strings)
        self.rewards = pickle_pack_dict['rewards']

    def __pickle_articles_dump(self):
        file_articles = self.config_file['pickle_articles']
        with open(file_articles, 'wb') as f:
            pickle.dump(self.articles, f)

    def __pickle_articles_load(self):
        file_articles = self.config_file['pickle_articles']
        with open(file_articles, 'rb') as f:
            self.articles = pickle.load(f)
