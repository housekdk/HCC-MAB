import unittest
import os
import socket
from newsbot import SlackNewsBot
import configparser
import pickle
import timeout_decorator


class TestNewsBotServer(unittest.TestCase):
    def setUp(self):
        if self.flag_articles is False:
            self.fail('Article dat file does not exist!')
        #if self.flag_socket is False:
        #    self.fail('Redirection Server does not exist!')

    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        # Refer to:
        # https://stackoverflow.com/questions/19196105/python-how-to-check-if-a-network-port-is-open-on-linux
        parent_folder = '../'
        # load configuration, init
        cls.config = configparser.ConfigParser()
        cls.config.read(parent_folder + 'config.ini')
        config_file = cls.config['FILE']
        config_server = cls.config['SERVER']
        config_slack = cls.config['SLACK']
        file_articles = parent_folder + config_file['pickle_articles']
        host = config_server['host']
        port = int(config_server['port'])

        cls.flag_articles = True if os.path.exists(file_articles) else False
        with open(file_articles, 'rb') as f:
            cls.articles = pickle.load(f)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)  # 2 Second Timeout
        result = sock.connect_ex((host, port))
        cls.flag_socket = True if result == 0 else False
        sock.close()
        cls.bot = SlackNewsBot(config_slack)

    # arm 개수가 config 파일의 arm 개수(number of variations)와 동일한지 체크
    @timeout_decorator.timeout(30)
    def test_is_successful_post_message(self):
        for article_df in self.articles:
            slack_msg_title = self.config.get('SLACK', 'message_title')
            slack_recipient = self.config.get('SLACK', 'recipient')
            #slack_recipient = '@daekeun.kim2'
            msg_text = datetime.datetime.now().strftime('*_{}, %Y/%m/%d %H:%M_*'.format(slack_msg_title))
            error_msg = None
            try:
                self.bot.post_message(slack_recipient, article_df, msg_text)
            except Exception as e:
                error_msg = e

            self.assertIsNone(error_msg)

if __name__ == '__main__':
    unittest.main()
