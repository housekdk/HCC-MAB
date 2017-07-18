[News Slack Bot Recommender Python Package]
======================

# Installation
### 필수 패키지 설치
```shell
$ pip install -r requirements.txt
```
### 설정 파일 수정
- config.ini.example 파일의 이름을 config.ini로 변경
- ini 파일 수정 (아래 참조)
```
[SERVER]
host = 127.0.0.1    # 실행 환경의 host를 입력 (기본값은 localhost)
port = 5000         # 실행 환경에서 열 port 번호를 입력 (Flask 기본값은 5000)
fresh_start = yes   # yes의 경우, 기존에 자동 저장된 MAB 알고리즘 정보와 기사 스크랩을 모두 삭제하고 시작

[SLACK]
token = your slack token           # https://api.slack.com 에서 제공받은 토큰을 입력
recipient = @id or /#channel       # 수신지가 사람이면 @, 채널이면 /#을 붙이고 입력
num_news_display = 10              # 한 번에 보낼 뉴스 기사 갯수
length_summary = 200               # 뉴스 기사 요약 문자열의 길이 제한
message_title = News               # 뉴스 모음 메시지를 보낼 때 메시지 제목
author_name = Featured             # 첫 번째 기사를 강조할 경우 (highlight_featured = yes) 나타낼 문자열
author_link = https://github.com   # 발신자를 누르면 이동하는 웹 링크
# footer = by News                 # 이를 주석(#)화하면, 각 뉴스마다 제공자를 출력함. 주석 해제하면 이 문자열로 대체
print_variation_info = yes         # 메시지 제목에, [CONTENT] 의 variation1~의 문자열을 같이 출력할지의 여부
shuffle = yes                      # yes일 경우 매번 가져오는 기사의 순서를 섞어 줌
highlight_featured = no            # yes의 경우 첫 번째 기사를 강조하여 출력
timeout = 300                      # slacker 패키지의 timeout 설정: 기본은 10

# highlight_featured = yes일 때 아바타 이미지
author_icon = https://avatars3.githubusercontent.com/u/162998?v=3&s=88

# 기사를 누를 때 링크가 깨졌다면, 대신 이 링크로 리다이렉션
default_redirect_link = https://github.com

[SCHEDULE]
# http://apscheduler.readthedocs.io/en/latest/modules/triggers/cron.html의 add_job()의 파라미터 설정 참조
day_of_week = mon-fri   # mon-fri 로 설정하면, 월요일에서 금요일까지 반복하여 실행함
hour = 8,13,18          # 8,13,18 로 설정하면, 8시, 13시, 18시마다 실행함

[CONTENTS]
# variation숫자 로 갯수 제한 없이 variation을 설정할 수 있음
mab_algorithm = EpsilonGreedyAlgorithm   # mab 패키지 (algorithm.py) 의 여러 알고리즘 중 하나의 클래스명을 기재
mab_algorithm_params = 0.1               # 해당 알고리즘에 입력될 매개변수를 지정: 쉼표(,)로 구분
variation1 = 인공지능,핀테크,데이터과학,연구     # variation 1~3: 이 키워드(들)로 구글 뉴스를 검색 (쉼표로 구분)
variation2 = 인공지능,게임,영화,연예
variation3 = 인공지능,날씨,재테크,정치

[FILE]
use_sqlite = yes                   # yes의 경우 sqlite_database를 사용하며, pickle_~ 파일은 사용하지 않음
sqlite_database = newsbot.db       # sqlite 데이터베이스 파일명
pickle_algorithm = algorithm.dat   # use_sqlite = no의 경우, mab 알고리즘 인스턴스를 저장할 파일명
pickle_articles = articles.dat     # use_sqlite = no의 경우, 스크랩한 기사들을 저장할 파일명
pickle_params = params.dat         # use_sqlite = no의 경우, mab와 관련된 다른 파라미터를 저장할 파일명
```
### 코드 실행
```shell
$ python mab_slack_newsbot_server.py
```
## [More Information (링크)](docs/README_MORE.md)
