import requests
from decouple import config
from bs4 import BeautifulSoup
from collections import Counter
import os
import json
import requests
import logging
import datetime
import re

subscription_key = config('subscription_key', default='')
# LANGUAGE_KEY = config('LANGUAGE_KEY', default='')
# LANGUAGE_ENDPOINT = config('LANGUAGE_ENDPOINT', default='')

search_url = "https://api.bing.microsoft.com/v7.0/search"

# This example requires environment variables named "LANGUAGE_KEY" and "LANGUAGE_ENDPOINT"
key = os.environ.get('LANGUAGE_KEY')
endpoint = os.environ.get('LANGUAGE_ENDPOINT')

from azure.ai.translation import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential

# Authenticate the client using your key and endpoint 
def authenticate_client():
    ta_credential = AzureKeyCredential(key)
    text_analytics_client = TextAnalyticsClient(
            endpoint=endpoint, 
            credential=ta_credential)
    return text_analytics_client

client = authenticate_client()

# Example method for summarizing text
def sample_extractive_summarization(client):
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.translation import (
        TextAnalyticsClient,
        ExtractiveSummaryAction
    ) 

    document = [
        "The extractive summarization feature uses natural language processing techniques to locate key sentences in an unstructured text document. "
        "These sentences collectively convey the main idea of the document. This feature is provided as an API for developers. " 
        "They can use it to build intelligent solutions based on the relevant information extracted to support various use cases. "
        "Extractive summarization supports several languages. It is based on pretrained multilingual transformer models, part of our quest for holistic representations. "
        "It draws its strength from transfer learning across monolingual and harness the shared nature of languages to produce models of improved quality and efficiency. "
    ]

    poller = client.begin_analyze_actions(
        document,
        actions=[
            ExtractiveSummaryAction(max_sentence_count=4)
        ],
    )

    document_results = poller.result()
    for result in document_results:
        extract_summary_result = result[0]  # first document, first result
        if extract_summary_result.is_error:
            print("...Is an error with code '{}' and message '{}'".format(
                extract_summary_result.code, extract_summary_result.message
            ))
        else:
            print("Summary extracted: \n{}".format(
                " ".join([sentence.text for sentence in extract_summary_result.sentences]))
            )

sample_extractive_summarization(client)

# print(search_results)

# 파파고를 이용한 translate
def get_translate(text):
    client_id = "qrCtFOINYuUF7VCgEKZK" # <-- client_id 기입
    client_secret = "cMmNOBq_i1" # <-- client_secret 기입

    data = {'text' : text,
            'source' : 'en',
            'target': 'ko'}

    url = "https://openapi.naver.com/v1/papago/n2mt"

    header = {"X-Naver-Client-Id":client_id,
              "X-Naver-Client-Secret":client_secret}

    response = requests.post(url, headers=header, data=data)
    rescode = response.status_code

    if(rescode==200):
        send_data = response.json()
        trans_data = (send_data['message']['result']['translatedText'])
        return trans_data
    else:
        print("Error Code:" , rescode)

# "distribution, logistics, trade, and crude oil, written in December 15th 2023"
# 한번에 하나의 토픽만을 쓰는 것이 정확도가 높다.
# 하나의 매체를 골라서 검색을 하는 것이 어렵다.
# 정확한 날짜를 골라서 검색 하는 것이 어렵다.
# 너무 자주 보내면 429 에러가 뜬다.

topic = 'financial'
search_term = f"{topic} issue today"

headers = {"Ocp-Apim-Subscription-Key": subscription_key}
params = {"q": search_term, "textDecorations": True, "textFormat": "HTML"}
response = requests.get(search_url, headers=headers, params=params)

response.raise_for_status()
search_results = response.json()

result_list = []

# https://api.bing.microsoft.com/v7.0/search를 이용했을때 있는 파라미터
pages = search_results['webPages']
results = pages['value']
# print(results)

# # https://api.bing.microsoft.com/v7.0/search 를 request 보냈을 떄 쓰일 수 있는 코드
name_date = []
for item in results:
    name = item['name']
    if "datePublished" not in item:
        continue 
    date_published = item['datePublished']
    name_date.append({'name': name, 'datePublished': date_published})

# # 추출된 결과 출력
# print(name_date)

# request to the result page that we get from the bing api
# 이렇게 하면 기사 하나만을 가져오는 작업을 못함. 왜냐하면 bing ai 가 검색하는 홈페이지를 알고, 
# 해당 body를 찾아서 내용물을 확인하는 작업인데, 그것이 반드시 기사 하나라고 보장을 할 수 없다.
for result in results[:10]:
    print(result['url'])
    response = requests.get(result['url'])
    soup = BeautifulSoup(response.content, 'html.parser')
    text = soup.find('body').get_text().strip()
    cleaned_text = ' '.join(text.split('\n'))
    cleaned_text = ' '.join(text.split())
    # print(cleaned_text)
    # if len is more than 10, then can count it
    counter = Counter(x for x in cleaned_text.split() if len(x) > 5)
    # find most common elements top 10
    elements_top10 = counter.most_common(10)
    # print(elements_top10)
    # # html data
    # content = response.content
    # print(content)
    # break

googlesheet_url = 'https://script.google.com/macros/s/AKfycbxZlEHhwBIiO-FmukfoyCHO1LX7VYqu8sdv2qwa8C_jmBdV3wWDbsGsq90uAVIrvL3P/exec'

if 'ENV' in os.environ:
    env = os.environ['ENV']
else:
    env = 'unkown'

@DeprecationWarning
def send_one(date1,date2,source,title1,title2,url):
    params = {
        'date1': date1,
        'date2': date2,
        'source': source,
        'title1': title1,
        'title2': title2,
        'url': url,
        'env': env
    }
    result = requests.post(googlesheet_url, headers=[], data=json.dumps(params), timeout=(30.0, 30.5)) # verify=False? connection timeout 10.0, read_timeout 10.5 
    logging.info(f'send_one({url})')


# https://docs.google.com/spreadsheets/d/1POoQiaHNosHJaHwJ-csg47mSAoyPMCTUrHgg_C3DaIU/edit?usp=sharing
NEWS_SHEET_URL = 'https://script.google.com/macros/s/AKfycbxk205v4AEJ8kLzLhUQbGae_9g4Wh2NM7QwX7CNPekQJmIcx8Y65nMFXdIkAl1HuQbt/exec'
def send_news(now, keyword, news_dt, source, title, title_mt, summary, url, rel):
    '''
    @param now        크롤링일시(현재일시)
    @param keyword    검색키워드
    @param news_dt    기사 날짜
    @param source     매체
    @param title      뉴스제목 원제
    @param title_mt   뉴스제목 번역
    @param summary    요약
    @param url        URL
    @param rel        관련도(빈값 입력)
    '''

    params = {
        'now': now,
        'keyword': keyword,
        'news_dt': news_dt,
        'source': source,
        'title': title,
        'title_mt': title_mt,
        'summary': summary,
        'url': url,
        'env': env,
        'rel': rel
    }
    result = requests.post(NEWS_SHEET_URL, headers=[], data=json.dumps(params), timeout=(30.0, 30.5)) # verify=False? connection timeout 10.0, read_timeout 10.5 
    logging.info(f'send_one({NEWS_SHEET_URL}) -> {result.status_code}')


# https://docs.google.com/spreadsheets/d/1B1zT210hUTUkdUz5upbLrRaHHOhwFzKTPdyWsceGuAs/edit?usp=sharing
NARAJANGTEO_SHEET_URL = 'https://script.google.com/macros/s/AKfycby96Mpv4cniEhIu3aJNZNsAZaW6Dl-BgWbM-jQDbrOyoL9VL-zp8d04x59Rk0dB74I_/exec'
def narajangteo(now, keyword, start_dt, bet_end_dt, pps_end_dt, amt, title, org, url):
    '''
    나라장터 시트에 저장한다.
    @param now        크롤링일시(현재일시)
    @param keyword    검색키워드
    @param start_dt   게시일시
    @param bet_end_dt 입찰마감일시
    @param pps_end_dt 제안서제출마감일시
    @param amt        사업금액
    @param title      공고명
    @param org        수요기관
    @param url        URL
    '''
    params = {
        'now': now,
        'keyword': keyword,
        'start_dt': start_dt,
        'bet_end_dt': bet_end_dt,
        'pps_end_dt': pps_end_dt,
        'amt': amt,
        'title': title,
        'org': org,
        'url': url,
        'env': env
    }
    result = requests.post(NARAJANGTEO_SHEET_URL, headers=[], data=json.dumps(params), timeout=(30.0, 30.5)) # verify=False? connection timeout 10.0, read_timeout 10.5 
    logging.info(f'send_one({NARAJANGTEO_SHEET_URL}) -> {result.status_code}')

if __name__ == '__main__':

    #send_one(1,2,3,4,5,6)

    # 인자값을 send_news 함수에 전달

    # 필요한 변수 준비
    now = datetime.datetime.now().isoformat()  # 현재 시간
    keyword = topic  # 검색 키워드
    rel = ''  # 관련도 (임의 값 또는 빈 문자열)

    # 정규 표현식 패턴: HTML 태그 제거
    html_tag_pattern = re.compile(r'<.*?>')

    # result_list에서 정보 추출 및 send_news 함수 호출
    for news_item in result_list:
        title = re.sub(html_tag_pattern, '', news_item['name'])
        print(f"title -> {title}")
        formatted_summary = re.sub(html_tag_pattern, '', news_item['description_trans'])
        print(f"formatted_summary -> {formatted_summary}")
        url = news_item['url']
        news_dt = news_item['datePublished'].split('T')[0]
        print(f"news_dt -> {news_dt}")
        source = news_item['provider']
        title_mt = re.sub(html_tag_pattern, '', news_item['name_trans'])
        send_news(now, keyword, news_dt, source, title, title_mt, formatted_summary, url, rel)
    

    #narajangteo(1,2,3,4,5,6,7,8,9)