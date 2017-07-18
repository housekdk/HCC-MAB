import mab
import newsbot
import re
import os
import pickle
import numpy as np
import pandas as pd
import datetime
import uuid
import requests
from flask import redirect
from peewee import *


# post news by using slacker api and get click rewards for mab variation selection
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
            self.__remove_file(file_params)
            self.__remove_file(file_algorithm)
            self.__remove_file(file_articles)

        self.database = None
        self.mab = None
        self.variation_strings = []
        self.num_variations = 0
        self.rewards = None
        self.articles = None

        # self.use_sqlite = True, then process information via sqlite3
        self.use_sqlite = True if self.config_file['use_sqlite'].upper() in {'YES', 'TRUE'} else False

        # load from database or files
        if self.use_sqlite:  # (database)
            file_sqlite = self.config_file['sqlite_database']
            # (database) connect
            if self.fresh_start:
                self.__remove_file(file_sqlite)
            self.db = SqliteDatabase(file_sqlite)
            self.database = newsbot.DatabaseNewsBot(self.db)

            # (database) load latest mab algorithm object and params
            self.mab, params = self.database.get_latest_object()
            if self.mab is not None:
                self.__unpack_params(params)
            else:
                self.__init_params()
                self.__init_algorithm()
        else:  # (pickle)
            # (pickle) load internal parameters
            if os.path.isfile(file_params):
                self.__pickle_params_load()  # load from pickled file
            else:
                self.__init_params()

            # (pickle) create a multi-armed bandit algorithm instance, or reload
            if os.path.isfile(file_algorithm):
                self.__pickle_algorithm_load()
            else:
                self.__init_algorithm()

            # (pickle) load all articles have served
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
        self.recipient = re.sub(r'/#|\\#', '#', self.recipient)  # remove escape '/' of '/#'
        self.print_variation_info =\
            True if self.config_slack['print_variation_info'].upper() in {'YES', 'TRUE'} else False
        self.shuffle = True if self.config_slack['shuffle'].upper() in {'YES', 'TRUE'} else False
        self.current_arm = None
        self.current_rewards = np.zeros(self.num_variations)
        self.current_article_df = pd.DataFrame()
        self.posted = False

    def __del__(self):
        if self.use_sqlite:
            self.db.close()

    def post_news(self):
        # dump all changing states on the previous post
        if self.posted:
            self.__save_states()

        self.current_arm = self.mab.select_arm()
        selected_variation = self.variation_strings[self.current_arm]
        article_df = self.scrapper.scrap_by_multiple_words(selected_variation)

        # post only unique news that have not been posted before
        if self.use_sqlite:
            not_in = []
            for row in article_df.itertuples():
                val = True if not self.database.is_exist_article(row.title) else False
                not_in.append(val)
            article_df = article_df[pd.Series(not_in, index=article_df.index.values)]
        else:
            new_titles = article_df['title'].values  # output: numpy array
            old_titles = np.array([])
            for i in range(self.num_variations):
                if len(self.articles[i]) != 0:
                    old_titles = np.append(old_titles, self.articles[i]['title'].values)
            unique_titles = np.setdiff1d(new_titles, old_titles)
            article_df = article_df[article_df['title'].isin(unique_titles)]  # remove old news

        # if there is no unique article in article_df, do nothing
        if len(article_df) == 0:
            self.current_article_df = article_df
            return

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

        # update self.articles (list of data frames)
        if not self.use_sqlite:
            self.articles[self.current_arm] = self.articles[self.current_arm].append(article_df, ignore_index=True)

        # post news messages to slack
        pref_msg_text = self.message_title
        if self.print_variation_info:
            pref_msg_text += ' ({})'.format(selected_variation)
        msg_text = datetime.datetime.now().strftime('*_{}, %Y-%m-%d %H:%M_*'.format(pref_msg_text))
        self.current_article_df = article_df
        self.posted = True
        try:
            self.bot.post_message(self.recipient, article_df, msg_text)
        except requests.exceptions.ReadTimeout:  # unpredictable errors of slacker api (leave logs if needed)
            pass

    def redirect_handler(self, path):
        arm = int(path.split('-')[0])
        self.current_rewards[arm] += 1

        df = self.current_article_df if self.use_sqlite else self.articles[arm]
        if len(df):
            match_condition = df['redirect_link'].str.contains(path)
            matched_df = df[match_condition]
            if len(matched_df) > 0:
                url = matched_df.iloc[0]['link']
                row_index = df[match_condition].index.values[0]  # row index of the first matched article
                clicks = df[match_condition].iloc[0]['clicks']  # and its cumulative click count
                df.set_value(row_index, 'clicks', clicks + 1)  # update the click count
                return redirect(url)

        if self.use_sqlite:
            url = self.database.get_link_and_update_clicks(path)
            if url is not None:
                return redirect(url)

        return redirect(self.config_slack['default_redirect_link'])

    # remove file if exists (otherwise, pass silently)
    @staticmethod
    def __remove_file(path):
        try:
            os.remove(path)
        except OSError:
            pass

    # initialize self.num_variations and self.rewards
    def __init_params(self):
        for key_str in self.config_content:
            if 'variation' in key_str:
                self.variation_strings.append(self.config_content[key_str])
        self.num_variations = len(self.variation_strings)
        self.rewards = [np.array([]) for i in range(self.num_variations)]  # list of empty numpy arrays

    # initialize self.mab
    def __init_algorithm(self):
        class_ = getattr(mab, self.config_content['mab_algorithm'])
        alg_params = self.config_content['mab_algorithm_params']
        if len(alg_params) > 0:
            alg_params = re.split('[\s,]+', self.config_content['mab_algorithm_params'])
            alg_params = [float(alg_param) for alg_param in alg_params]  # string to text
            self.mab = class_(self.num_variations, *alg_params)
        else:
            self.mab = class_(self.num_variations)

    def __save_states(self):
        self.rewards[self.current_arm] =\
            np.append(self.rewards[self.current_arm], self.current_rewards[self.current_arm])
        self.mab.update(self.current_arm, self.current_rewards[self.current_arm])  # update algorithm state
        self.current_rewards = np.zeros(self.num_variations)

        if self.use_sqlite:
            for row in self.current_article_df.itertuples():
                self.database.insert_article(row, self.current_arm)
            self.database.insert_object(self.mab, self.__pack_params())
        else:
            self.__pickle_algorithm_dump()
            self.__pickle_params_dump()
            self.__pickle_articles_dump()

    def __pack_params(self):
        return {'variation_strings': self.variation_strings, 'rewards': self.rewards}

    def __unpack_params(self, pack_dict):
        self.variation_strings = pack_dict['variation_strings']
        self.num_variations = len(self.variation_strings)
        self.rewards = pack_dict['rewards']

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
        with open(file_params, 'wb') as f:
            pickle.dump(self.__pack_params(), f)

    def __pickle_params_load(self):
        file_params = self.config_file['pickle_params']
        with open(file_params, 'rb') as f:
            pickle_pack_dict = pickle.load(f)
        self.__unpack_params(pickle_pack_dict)

    def __pickle_articles_dump(self):
        file_articles = self.config_file['pickle_articles']
        with open(file_articles, 'wb') as f:
            pickle.dump(self.articles, f)

    def __pickle_articles_load(self):
        file_articles = self.config_file['pickle_articles']
        with open(file_articles, 'rb') as f:
            self.articles = pickle.load(f)
