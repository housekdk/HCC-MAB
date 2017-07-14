# mab_slack_newsbot_server.py
# by Byonghwa Oh, 20170714

# posts some news to the slack recipient (user or channel) and optimizes CTR with multi-armed bandit algorithm
# please modify 'config.ini' (copy from 'config.ini.example') for initial start-up

import atexit
import configparser
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from newsbot.mab_slack_newsbot import MABSlackNewsBot


# load configuration, init
config = configparser.ConfigParser()
config.read('config.ini')
host = config.get('SERVER', 'host')
port = int(config.get('SERVER', 'port'))
cron_day_of_week = config.get('SCHEDULE', 'day_of_week')
cron_hour = config.get('SCHEDULE', 'hour')

# news bot
mab_bot = MABSlackNewsBot(config)

# scheduler
cron = BackgroundScheduler()
cron.start()
atexit.register(lambda: cron.shutdown())  # when the server terminates, remove the scheduler

# for every monday ~ friday at 8:00, 13:00, 18:00, the post_news() is executed
# Refer to: http://apscheduler.readthedocs.io/en/latest/modules/triggers/cron.html
# cron.add_job(func=mab_bot.post_news, trigger='cron', minute='*/20', replace_existing=True)  # test (every 10 minute)
cron.add_job(func=mab_bot.post_news, trigger='cron',
             day_of_week=cron_day_of_week, hour=cron_hour, replace_existing=True)

# flask web server
app = Flask(__name__)


# Catch-All URL
# Refer to: http://flask.pocoo.org/snippets/57/
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def redirect_handler(path):
    return mab_bot.redirect_handler(path)


if __name__ == '__main__':
    app.run(host, port)  # flask server run
