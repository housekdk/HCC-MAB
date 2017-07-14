from slacker import Slacker
import datetime


class SlackNewsBot:
    def __init__(self, config_dict):
        self.config_dict = config_dict
        self.slack = Slacker(config_dict['token'])
        self.num_display = int(config_dict['num_news_display'])
        self.length_summary = int(config_dict['length_summary'])
        self.highlight_featured = True if config_dict['highlight_featured'].upper() in {'YES', 'TRUE'} else False
        self.attachments = []
        self.current_df = None

        # 뉴스 주제별 color 정보
        self.slack_color_dict = {0: '#8904B1', 1: '#0404B4', 2: '#B92323',
                                 6: '#26FF92', 7: '#FF00BF', 8: '#424242'}

    def post_message(self, recipient, article_df, msg_text=None, as_user=True):
        if msg_text is None:
            msg_text = datetime.datetime.now().strftime('*_%Y/%m/%d %H:%M_*')
        self.slack.chat.post_message(recipient, msg_text,
                                     attachments=self.__generate_attachments(article_df), as_user=as_user)

    def __generate_attachments(self, article_df):
        self.attachments[:] = []  # clear the old attachments
        for idx in range(len(article_df)):
            if idx == self.num_display:
                break
            if idx == 0 and self.highlight_featured:
                is_featured = True
            else:
                is_featured = False
            self.attachments.append(self.__get_slack_message_for_selected_news(article_df.iloc[idx], is_featured))
        return self.attachments

    def __get_slack_message_for_selected_news(self, df_sub, is_featured):
        title = df_sub['title']
        summary = df_sub['summary']
        redirect_link = df_sub['redirect_link']
        image = df_sub['image']
        dic = dict()

        if is_featured:
            dic['image_url'] = image
            dic['color'] = self.slack_color_dict[0]
            dic['author_name'] = self.config_dict['author_name']
            dic['author_link'] = self.config_dict['author_link']
            dic['author_icon'] = self.config_dict['author_icon']
        else:
            dic['thumb_url'] = image

        dic['title'] = title
        dic['title_link'] = redirect_link
        if self.length_summary is not None:
            summary = summary[0:self.length_summary]
        dic['fallback'] = summary + '...'
        dic['text'] = summary + '...'
        dic['footer'] = self.config_dict['footer']
        dic['mrkdwn_in'] = ["author_name", "text", "pretext"]

        return dic
