 [Slack News Bot Python Package - More Information]
======================

# 1. 개요
### 1.1. 어떤 것을 할 수 있나요?
#### 구글 뉴스 메세징
- **slack_newsbot_server.py**, **mab_slack_newsbot_server.py** (*MAB 버전*)
- 구글 뉴스의 기사들을 정해진 스케줄에 따라 자동으로 스크래핑합니다.
- 정해진 시간마다 Slack News Bot으로 사용자에게 추천 뉴스들을 보내 줍니다.
- MAB 버전의 경우는,
  - **Multi-Armed Bandit** 알고리즘을 사용하여,
  - *config.ini* 파일 안에 정의한 여러 Variation 중 하나의 Variation에 대한 기사를 보내는데,
  - 사용자 클릭수를 즉각적으로 반영하여 수신자가 더 좋아할 만한 Variation으로 선택하여 보내 줍니다.
- References
  - [구글 뉴스](https://news.google.com)
#### MAB 알고리즘 벤치마킹
- *examples* 안의 여러 스크립트를 사용하여 MAB 알고리즘의 벤치마킹을 할 수 있습니다.
- 특히, **Yahoo! News Front Page Today** 데이터셋을 활용해, MAB (Contextual 포함) 알고리즘들에 대한 성능 평가를 할 수 있습니다.
  - 야후 데이터는 공개가 금지되기 때문에, 직접 야후에 데이터 파일을 요청하여 다운로드 후, *yahoo_r6_to_sqlite.py* 를 실행하여 SQLite DB를 만들어야 합니다.
  - *yahoo_r6_to_sqlite.py* 에서는 *process_to_sqlite.py* 에서 *ProcessWebscope* 를 Import하기에, 다음 링크에서 해당 파일을 다운로드받아서 사용하면 됩니다.
  - https://github.com/j-wang/BanditEmpirical/blob/master/process_to_sqlite.py
  - *yahoo_r6_full.db* 가 만들어지면, *examples* 안의 야후 관련 실험을 수행할 수 있습니다.
- References
  - [Yahoo! News Front Page Today Dataset ](https://webscope.sandbox.yahoo.com/catalog.php?datatype=r)
  - [L. Li et al., A Contextual-Bandit Approach to
Personalized News Article Recommendation (2010)](https://arxiv.org/pdf/1003.0146.pdf)
  - [L. Li et al., Unbiased offline evaluation of contextual-bandit-based news article recommendation algorithms (2012)](https://arxiv.org/pdf/1003.0146.pdf)
### 1.2. 앞으로 추가 및 개선할 기능은?
- 뉴스의 Main Text를 더 정교하게 스크랩하는 것
- 메세징 UI 개선 (좀 더 사용자 친화적으로)

# 2. Specifications
### 2.1. Environments
- Python 3.6 or Higher
- [PyCharm Community Edition 2017.1.4](https://www.jetbrains.com/pycharm/)
- [Slack](https://slack.com/)
### 2.2. Packages
- numpy>=1.11.3
- pandas>=0.20.1
- slacker>=0.9.50
- scipy>=0.19.0
- beautifulsoup4>=4.6.0
- scikit_learn>=0.18.1
- SQLAlchemy>=1.1.11
- Flask>=0.12.2
- apscheduler>=3.3.1
- gnewsclient>=1.0.2
- newspaper3k>=0.2.2
- peewee>=2.10.1
- timeout-decorator>=0.3.3
### 2.3. Folders
    .
    ├── examples                      # MAB 알고리즘 실행 예제 모음
    ├── mab                           # MAB 알고리즘 패키지 (일반 및 Contextual 알고리즘 포함)
    ├── newsbot                       # News Slack Bot 기능 구현
    ├── test                          # Unit Test 관련
    ├── (Webscope)                    # Yahoo! News Front Page Today Dataset (R6) 의 저장 경로
    │   ├── (R6)                      # R6의 저장 경로: ydata-fp-td-clicks-v1_0.20090501.gz, ...
    ├── (yahoo_r6)                    # process_to_sqlite.py 가 위치할 경로
    └── mab_slack_newsbot_server.py   # MAB를 사용한 Slack News Bot 서버
# 3. Issues
- 코드에 대한 이슈나 개선점이 필요하면 Pull Request를 통해 요청해 주세요.
- Pull Request 사용법: TODO

### [README.md로 돌아가기](../README.md)
