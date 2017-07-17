# redirection web server w/ scheduler
# by Byonghwa Oh, 20170714

# just crawls news with the keywords in [CONTENTS]:variation1, and posts them to the recipient (slack user or channel)
# please modify 'config.ini' (copy from 'config.ini.example') for initial start-up

from flask import Flask, redirect
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from newsbot import SlackNewsBot, NewsScrapperGoogle
import datetime
import configparser
import uuid
import pickle


# load configuration, init
config = configparser.ConfigParser()
config.read('config.ini')
host = config.get('SERVER', 'host')
port = int(config.get('SERVER', 'port'))
server_url = 'http://{}:{}/'.format(host, port)
slack_msg_title = config.get('SLACK', 'message_title')
slack_recipient = config.get('SLACK', 'recipient')
contents = config.get('CONTENTS', 'variation1')
file_pickle = 'temp_dump.dat'
cron_day_of_week = config.get('SCHEDULE', 'day_of_week')
cron_hour = config.get('SCHEDULE', 'hour')

# scheduler
cron = BackgroundScheduler()
cron.start()
atexit.register(lambda: cron.shutdown())  # when the server terminates, remove the scheduler

# news scrapper & bot
scrapper = NewsScrapperGoogle()
bot = SlackNewsBot(config['SLACK'])

# flask web server
app = Flask(__name__)


# Catch-All URL
# Refer to: http://flask.pocoo.org/snippets/57/
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def redirect_handler(path):
    with open(file_pickle, 'rb') as f:
        article_df = pickle.load(f)
    redirection_url = article_df.loc[article_df['redirect_link'] == server_url + path].iloc[0]['link']
    return redirect(redirection_url)


# Refer to: https://stackoverflow.com/questions/21214270/flask-run-function-every-hour
def post_news():
    msg_text = datetime.datetime.now().strftime('*_{}, %Y-%m-%d %H:%M_*'.format(slack_msg_title))
    article_df = scrapper.scrap_by_multiple_words(contents)

    redirect_urls = []
    for idx in range(len(article_df)):
        redirect_urls.append(server_url + str(uuid.uuid4()))
    article_df['redirect_link'] = redirect_urls

    with open(file_pickle, 'wb') as f:
        pickle.dump(article_df, f)

    bot.post_message(slack_recipient, article_df, msg_text)


# for every monday ~ friday at 8:00, 13:00, 18:00, the post_news() is executed
# Refer to: http://apscheduler.readthedocs.io/en/latest/modules/triggers/cron.html
# cron.add_job(func=post_news, trigger='cron', minute='*/10', replace_existing=True)  # test (every 10 minute)
cron.add_job(func=post_news, trigger='cron', day_of_week=cron_day_of_week, hour=cron_hour, replace_existing=True)


if __name__ == '__main__':
    # flask server run
    app.run(host, port)
