from gnewsclient import gnewsclient
import pandas as pd
import numpy as np
from newspaper import Article
import urllib.parse as up
import urllib.request as ur
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import html.parser as hp


class NewsScrapperNaver(object):
    def __init__(self, parse_text_with_newspaper=False):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; ko-KR))'}
        self.main_url = 'http://m.news.naver.com'
        self.get_news_url = self.main_url + '/read.nhn?oid={}&aid={}'
        self.popular_url = self.main_url + '/rankingList.nhn?sid1=&date='
        self.desktop_url = 'http://news.naver.com/main/read.nhn?oid={}&aid={}'
        self.search_prefix = 'http://news.search.naver.com/search.naver?where=news&sm=tab_jum&ie=utf8&query='
        self.current_soup = None
        self.current_url = None
        self.current_text = ''
        self.parse_text_with_newspaper = parse_text_with_newspaper  # false: use get_text_using_newspaper()

        # 뉴스 주제
        self.news_subject_dict = {0: '정치', 1: '경제', 2: '사회',
                                  3: 'IT', 4: '생활', 5: '세계',
                                  6: '연예', 7: '포토', 8: 'TV'}

        # 뉴스 주제별 랭킹 뉴스 (총 주제 9건, 주제별 추천 뉴스 3건이므로 총 추천 뉴스 건수는 27건)
        self.news_subject = ['politics', 'economy', 'society', 'it_secience',
                             'life_culture', 'world', 'entertainments', 'photo_section', 'tv_section']

        # 네이버 주제별 랭킹 뉴스를 검색하기 위한 정규식 표현
        # 예: 정치 뉴스 => politics1, politics2, politics3
        self.news_subject_regexp = ''
        for k in range(0, len(self.news_subject)):
            self.news_subject_regexp += (self.news_subject[k] + '[0-9]|')
        self.news_subject_regexp = self.news_subject_regexp[:-1]

    def scrap_by_title(self, title):  # e.g. MS, 시각 장애인을 위한 인공지능 앱 '씨잉 AI' 출시
        search_url = self.search_prefix + up.quote(title)
        response = requests.get(search_url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'lxml')
        search_results = soup.find('ul', {'class': 'type01'})  # get every search results
        if search_results is None:
            return None
        item = search_results.findAll('li')[0]  # use the first search link only
        hyperlinks = item.findAll('a')
        target_idx = None
        for idx, link in enumerate(hyperlinks):  # if the news is already processed by naver, get the link
            if '네이버뉴스' in link.text:
                target_idx = idx
                break
        if target_idx is None:
            return None
        return self.scrap_by_url(hyperlinks[target_idx]['href'])

    def scrap_by_url(self, url):  # e.g. http://m.news.naver.com/read.nhn?oid=045&aid=0002155350
        self.current_url = self.__get_mobile_url(url)
        response = requests.get(self.current_url, headers=self.headers)
        self.current_soup = BeautifulSoup(response.text, 'lxml')
        title = self.__get_title()
        return {'title': title,
                'provider': self.__get_provider(),
                'date': self.__get_date(),
                'link': self.__get_desktop_url(self.current_url),
                'image': self.__get_image(),
                'summary': self.__get_summary(),
                'text': self.__get_text(),
                'text_num_words': self.__get_text_number_of_words(),
                'title_features': self.__get_title_features(title)}

    def scrap_popular(self, num_days_ago=0):  # from, http://m.news.naver.com/rankingList.nhn
        date_num_days_ago = (datetime.now() - timedelta(days=num_days_ago)).strftime("%Y%m%d")
        response = ur.urlopen(self.popular_url + date_num_days_ago)
        soup = BeautifulSoup(response, 'lxml')
        articles_df = pd.DataFrame()

        # Find all news subjects such as politics, economy, and so on
        articles = soup.find_all('li', id=re.compile(self.news_subject_regexp))
        subject_idx = 0  # news subject index (0~8)
        for idx, item in enumerate(articles):
            visit = (item.find('div', class_='commonlist_tx_visit')).get_text()
            visit = int(visit[3:].replace(',', ''))  # 조회수1000 => 1000
            title_link = item.select('a')
            news_url = title_link[0]['href']
            scrap_dict = self.scrap_by_url(news_url)
            scrap_dict.update({'subject': self.news_subject_dict[subject_idx], 'num_visits': visit})
            if (idx + 1) % 3 == 0:  # three articles per category
                subject_idx += 1
            articles_df = articles_df.append(scrap_dict, ignore_index=True)

        return articles_df

    @staticmethod
    def __parse_url(url):
        parsed_url = up.urlparse(url)
        params = up.parse_qs(parsed_url.query)
        return {'oid': params['oid'][0], 'aid': params['aid'][0]}

    def __get_mobile_url(self, url):
        params = self.__parse_url(url)
        return self.get_news_url.format(params['oid'], params['aid'])  # change url to mobile url

    def __get_desktop_url(self, url):
        params = self.__parse_url(url)
        return self.desktop_url.format(params['oid'], params['aid'])  # change url to desktop(full-sized) url

    def __get_property(self, property_name):
        content = str(self.current_soup.find('meta', property=property_name))
        content = re.sub('<meta content=["|\']', '', content, 0, re.I | re.S)
        reg_ex = '["|\'] property="{}"/>'.format(property_name)
        content = re.sub(reg_ex, '', content, 0, re.I | re.S)
        return content

    def __get_title(self):
        return self.__get_property('og:title')

    def __get_image(self):
        return self.__get_property('og:image')

    def __get_summary(self):
        return self.__get_property('og:description')

    def __get_date(self):
        date_area = self.current_soup.find('span', class_='media_end_head_info_datestamp_time')
        if date_area is None:
            date_area = self.current_soup.find('span', class_='t11')
        if date_area is None:
            return ''
        else:
            return date_area.text

    def __get_text(self, remove_email=False, remove_special_chars=False):
        if self.parse_text_with_newspaper:
            return self.__get_text_using_newspaper()

        text = ''
        text_area = self.current_soup.find_all('div', id='dic_area')
        if len(text_area) == 0:
            text_area = self.current_soup.find_all('div', class_='newsct_body')

        for item in text_area:
            adding = str(item.find_all(text=True))
            # adding = re.sub('^[^ㄱ-ㅣ가-힣]+', '', adding)  # remove preceding non-hangul
            text = text + adding

        text = hp.unescape(text)  # remove escaped entities from text

        if remove_email:
            email_match = re.search('[a-zA-Z0-9\._+]+@', text)
            if email_match is not None:
                email_loc = email_match.start()
                text = text[:email_loc]

        if remove_special_chars:
            text = re.sub('[a-zA-Z]', '', text)
            text = re.sub('[\{\}\[\]\/?.,;:|\)*~`!^\-_+<>@\#$%&\\\=\(\'\"]', '', text)

        text = re.sub(r'^(\[)*(\\n|\\r|\\t|\s|\'|\"|,)*', '', text)
        self.current_text = text
        return self.current_text

    def __get_text_using_newspaper(self):
        news_obj = Article(self.current_url, language='ko')
        news_obj.download()
        news_obj.parse()
        self.current_text = news_obj.text
        return self.current_text

    def __get_text_number_of_words(self):
        if len(self.current_text) == 0:
            self.__get_text()
        number_of_words = len(re.findall(r'\w+', self.current_text))
        return number_of_words

    def __get_provider(self):
        creator_list = self.current_soup.find_all('meta', {'name': 'twitter:creator'})
        if len(creator_list) == 1:
            creator = str(creator_list[0])
            creator = re.sub('<meta content=["|\']', '', creator, 0, re.I | re.S)
            creator = re.sub('["|\'] name="twitter:creator"/>', '', creator, 0, re.I | re.S)
            return creator
        else:
            return ''

    @staticmethod
    def __get_title_features(title):
        # 제목 길이
        title_length = len(title)

        # 제목[] 등장 유무
        pattern = re.compile('\[.+\]')
        is_emphasis = False
        if pattern.match(title):
            is_emphasis = True

        # 말줄임(...) 빈도
        pattern = re.compile('[.]{2,4}', re.I | re.S)
        pattern_iterator = re.finditer(pattern, title)
        num_omitted = sum(1 for _ in pattern_iterator)

        feat_dic = {'title_length': title_length, 'is_emphasis': is_emphasis, 'num_omitted': num_omitted}
        return feat_dic


class NewsScrapperGoogle(object):
    def __init__(self, scrap_content_from_naver=True, len_summary=None, ignore_urls=None):
        self.client = gnewsclient()
        self.client.language = 'korean'  # default language is Korean
        self.naver_scrapper = None
        self.scrap_content_from_naver = scrap_content_from_naver
        self.naver_scrapper = NewsScrapperNaver()
        self.len_summary = len_summary
        self.ignore_urls = ignore_urls

    def scrap_by_word(self, word):
        self.client.query = word
        google_news = self.client.get_news()
        df_columns = ['title', 'provider', 'date', 'link', 'image', 'summary', 'text']
        article_df = pd.DataFrame()

        for idx, article in enumerate(google_news):
            target = pd.Series(['' for i in range(len(df_columns))], df_columns)
            title_split = article['title'].split(' - ')
            if len(title_split) > 1:
                # target['title'] = ' - '.join(title_split[:len(title_split) - 1])
                target['title'] = title_split[0]  # valid if there are no ' - ' in the title, but...
                target['provider'] = title_split[len(title_split) - 1]
            else:
                target['title'] = article['title']
                target['provider'] = ''

            # scrap with NaverNewsScrapper
            if self.scrap_content_from_naver:
                news_dict = self.naver_scrapper.scrap_by_title(target['title'])
                if news_dict is not None:
                    for key in df_columns[1:]:
                        target[key] = news_dict[key]
                    article_df = article_df.append(target, ignore_index=True)
                    continue

            link = article['link']  # always exist

            # process ignore url list
            if self.ignore_urls is not None:
                flag_discard = False
                for url in self.ignore_urls:
                    if url in link:
                        flag_discard = True
                        break
                if flag_discard:
                    continue

            # scrap with newspaper
            target['link'] = up.unquote(link) if '%' in link else link  # correction: decode non-us strings in the url
            news_obj = Article(target['link'], language='ko')  # default language is Korean
            news_obj.download()
            if news_obj.download_state == 2:  # if the download succeeds,
                news_obj.parse()
                target['image'] = '' if news_obj.top_image is None else news_obj.top_image
                date = '' if news_obj.publish_date is None else news_obj.publish_date
                target['date'] = date if type(date) is str else date.strftime('%Y-%m-%d %H:%M:%S')  # what the...
                target['text'] = news_obj.text  # always exist

                summary_text = re.sub(r'(\\r|\\n|\\t|\s)+', ' ', target['text'])
                if self.len_summary is None:
                    target['summary'] = summary_text
                else:
                    target['summary'] = summary_text[:self.len_summary]

                article_df = article_df.append(target, ignore_index=True)

        return article_df

    def scrap_by_multiple_words(self, words):
        if type(words) is str:
            words = re.split('[\s,]+', words)

        if len(words) == 1:
            if type(words) is dict:
                words = [list(words.keys())[0]]

        article_df = pd.DataFrame()
        num_words = len(words)
        for word_idx, word in enumerate(words):
            articles = self.scrap_by_word(word)
            articles['subject'] = np.repeat(word, len(articles))
            articles['priority'] = np.arange(word_idx, len(articles) * num_words, num_words)
            article_df = article_df.append(articles, ignore_index=True)
        article_df = article_df.sort_values('priority').reset_index(drop=True).\
            drop('priority', 1).drop_duplicates(['link'])
        return article_df
