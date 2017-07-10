# redirection web server w/ scheduler

from flask import Flask, redirect, request
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from newsbot import common_params as cp
from newsbot import NewsScrapper
from newsbot import SlackNewsBot
import datetime
import configparser


# load configuration
config = configparser.ConfigParser()
config.read('config.ini')
host = config.get('SERVER', 'host')
port = int(config.get('SERVER', 'port'))
slack_token = config.get('SLACK', 'token')
slack_recipient = config.get('SLACK', 'recipient')
slack_msg_title = config.get('SLACK', 'message_title')
slack_num_display = int(config.get('SLACK', 'num_news_display'))
slack_len_desc = int(config.get('SLACK', 'length_description'))

# scheduler
cron = BackgroundScheduler()
cron.start()
atexit.register(lambda: cron.shutdown())  # when the server terminates, remove the scheduler

# news scrapper & bot
params = cp.CommonParams(slack_token, host, port, slack_num_display, slack_len_desc)
scrapper = NewsScrapper(params)
scrapper.scrap()
bot = SlackNewsBot(params)

# flask web server
app = Flask(__name__)


# Catch arguments: https://stackoverflow.com/questions/40658566/question-marks-in-flask-urls-for-routing
# Example URL: 127.0.0.1:5000/alab.ml?sorder=3&aorder=10&oid=008&aid=0003894436&sid1=105&date=20170627&ntype=RANKING
@app.route('/alab.ml', methods=['GET'])
def redirect_handler():
    # resolve request path string then reroute
    # subject_order = request.args.get('sorder')
    # article_order = request.args.get('aorder')
    oid = request.args.get('oid')
    aid = request.args.get('aid')
    redirection_url = 'http://news.naver.com/main/read.nhn?oid={}&aid={}'.format(oid, aid)
    return redirect(redirection_url)


# Refer to: https://stackoverflow.com/questions/21214270/flask-run-function-every-hour
def post_news():
    msg_text = (datetime.datetime.now()).strftime('*_{}, %Y/%m/%d %H:%M_*'.format(slack_msg_title))
    bot.slack.chat.post_message(slack_recipient, msg_text, attachments=bot.post_message(0, True), as_user=True)


# for every monday ~ friday at 8:00, 13:00, 18:00, the post_news() is executed
# Refer to: http://apscheduler.readthedocs.io/en/latest/modules/triggers/cron.html
# cron.add_job(func=post_news, trigger='interval', seconds=10, replace_existing=True)  # testing (every 10 sec)
cron.add_job(func=post_news, trigger='cron', day_of_week='mon-fri', hour='8,13,18', replace_existing=True)


if __name__ == '__main__':
    # flask server run
    app.run(host=params.server_address, port=params.server_port)
