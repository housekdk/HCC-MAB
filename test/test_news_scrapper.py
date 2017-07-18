import configparser
import unittest
import pandas as pd
import pickle
import urllib
import re
import os
import sqlite3


class TestNewsScrapperCommon:
    def __init__(self, articles):
        self.articles = articles

    def is_url_valid_df_column(self, column_name):
        list_error_row_count = []
        for article_df in self.articles:
            error_row_count = 0
            test_column = article_df[column_name]
            for url in test_column:
                if self.__is_url_valid(url) is False:
                    error_row_count += 1
            list_error_row_count.append(error_row_count)
        return list_error_row_count

    def is_string_contains_html_character(self, column_name):
        pattern = re.compile('.*\&(nbsp|quot|amp|lsquo|rsquo|ldquo|rdquo);.*')
        list_error_row_count = []
        for article_df in self.articles:
            error_row_count = 0
            test_column = article_df[column_name]
            for str in test_column:
                if pattern.search(str) is True:
                    error_row_count += 1
                list_error_row_count.append(error_row_count)
            return list_error_row_count

    @staticmethod
    def __is_url_valid(url, qualifying=None):
        min_attributes = ('scheme', 'netloc')
        qualifying = min_attributes if qualifying is None else qualifying
        token = urllib.parse.urlparse(url)
        return all([getattr(token, qualifying_attr)
                    for qualifying_attr in qualifying])


class TestNewsScrapper(unittest.TestCase):
    def setUp(self):
        if self.flag_articles is False:
            self.fail('Article dat file does not exist!')

    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        parent_folder = '../'
        # load configuration, init
        cls.config = configparser.ConfigParser()
        cls.config.read(parent_folder + 'config.ini')
        config_file = cls.config['FILE']
        config_content = cls.config['CONTENTS']
        cls.num_variations = 0
        for key_str in config_content:
            if 'variation' in key_str:
                cls.num_variations += 1

        use_sqlite = True if config_file['use_sqlite'].upper() in {'YES', 'TRUE'} else False
        if use_sqlite:
            cls.articles = []
            sqlite_articles = parent_folder + config_file['sqlite_database']
            cls.flag_articles = True if os.path.exists(sqlite_articles) else False

            con = sqlite3.connect(sqlite_articles)
            query = 'SELECT * FROM article WHERE variation='
            for i in range(cls.num_variations):
                table = pd.read_sql_query(query + str(i), con)
                cls.articles.append(table)
            con.close()
        else:
            file_articles = parent_folder + config_file['pickle_articles']
            cls.flag_articles = True if os.path.exists(file_articles) else False
            with open(file_articles, 'rb') as f:
                cls.articles = pickle.load(f)

        cls.column_names = cls.articles[0].columns.values
        cls.tc = TestNewsScrapperCommon(cls.articles)

    # arm 개수가 config 파일의 arm 개수(number of variations)와 동일한지 체크
    def test_num_arms(self):
        self.assertEqual(self.num_variations, len(self.articles))

    # 뉴스 데이터의 empty 여부 체크
    def test_is_article_empty(self):
        for article_df in self.articles:
            for column_name in self.column_names:
                self.assertFalse(article_df[column_name].empty)

    # 뉴스일자가 등록되었는지 체크
    @unittest.expectedFailure
    def test_is_date_exists(self):
        for article_df in self.articles:
            self.assertFalse('' in article_df['date'].values)

    # 뉴스 데이터의 null값 포함 여부 체크
    def test_is_article_contains_null(self):
        for article_df in self.articles:
            null_sum = pd.isnull(article_df).sum()
            error_row_count = 0
            for k in range(len(self.column_names)):
                error_row_count += null_sum[self.column_names[k]]

            self.assertEqual(0, error_row_count)

    # 신문사가 적정 길이인지 체크 (e.g., 연합뉴스 -> OK)
    def test_is_provider_too_long(self):
        pattern = re.compile('.*[a-zA-Z0-9]+.*')
        for article_df in self.articles:
            for row in article_df.itertuples():
                val = row.provider
                len_provider = len(val)
                len_limit = 30 if pattern.search(val) else 15
                self.assertTrue(len_provider < len_limit)

    # image URL이 잘 접속되는지 체크
    def test_is_valid_image_url(self):
        list_error_row_count = self.tc.is_url_valid_df_column('image')
        for error_row_count in list_error_row_count:
            self.assertEqual(0, error_row_count)

    # 뉴스 본문 링크가 잘 접속되는지 체크
    def test_is_valid_link_url(self):
        list_error_row_count = self.tc.is_url_valid_df_column('link')
        for error_row_count in list_error_row_count:
            self.assertEqual(0, error_row_count)

    # 뉴스 제목 내 html 특수문자 포함 여부 체크
    def test_is_title_contains_html_character(self):
        list_error_row_count = self.tc.is_string_contains_html_character('title')
        for error_row_count in list_error_row_count:
            self.assertEqual(0, error_row_count)

    # 뉴스 요약 내 html 특수문자 포함 여부 체크
    def test_is_summary_contains_html_character(self):
        list_error_row_count = self.tc.is_string_contains_html_character('summary')
        for error_row_count in list_error_row_count:
            self.assertEqual(0, error_row_count)

    # 뉴스 요약 내 날짜 정보가 과도하게 많이 들어가 있는지 체크 (날짜는 뉴스 요약에서 0번이나 1번만 등장해야 함)
    def test_is_summary_contains_multiple_dates(self):
        pattern = re.compile(
            '\d{4}[년|\.]\s{0,1}\d{2}[월|\.]\s{0,1}\d{2}\s{0,1}일{0,1}\s{0,1}\d{2}[시|:]\s{0,1}\d{2}분{0,1}')

        for article_df in self.articles:
            for row in article_df.itertuples():
                val = row.summary
                find_list = pattern.findall(val)
                self.assertLessEqual(len(find_list), 1)

    # 뉴스 제목 길이가 60자 이하인지 체크
    def test_is_title_too_long(self):
        for article_df in self.articles:
            len_title = article_df['title'].apply(len)
            self.assertTrue(any(len_title < 60))


if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNewsScrapper)
    test_result = unittest.TextTestRunner(verbosity=2).run(suite)
