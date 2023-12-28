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
from azure.ai.translation.text import TextTranslationClient, TranslatorCredential
from azure.ai.translation.text.models import InputTextItem
from azure.core.exceptions import HttpResponseError

subscription_key = config('subscription_key', default='')
LANGUAGE_KEY = config('LANGUAGE_KEY', default='')
LANGUAGE_ENDPOINT = config('LANGUAGE_ENDPOINT', default='')
TRANSLATOR_KEY = config('TRANSLATOR_KEY', default='')
API_REGION = config('API_REGION', default='')
TRANSLATOR_ENDPOINT = config('TRANSLATOR_ENDPOINT', default='')

search_url = "https://api.bing.microsoft.com/v7.0/news/search"
# "distribution, logistics, trade, and crude oil, written in December 15th 2023"
# 한번에 하나의 토픽만을 쓰는 것이 정확도가 높다.
# 하나의 매체를 골라서 검색을 하는 것이 어렵다.
# 정확한 날짜를 골라서 검색 하는 것이 어렵다.
# 너무 자주 보내면 429 에러가 뜬다.
# 쓸데없는 url도 보내서 정확도가 낮다.
# bing을 통한 검색 결과를 내보내는 것으로, ai에게 질문하듯이 query를 짜는 것이 아닌, 웹검색 하듯이 query를 짜야 한다.

topic = 'crude oil'
search_term = f"{topic} news in English article in December 2023"

headers = {"Ocp-Apim-Subscription-Key": subscription_key}
params = {"q": search_term, "textDecorations": True, "textFormat": "HTML"}
response = requests.get(search_url, headers=headers, params=params)
response.raise_for_status()
search_results = response.json()
# print(search_results)
news_list = search_results['value']

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
# 현재 안쓰고있음.
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

# sample_extractive_summarization(client)

credential = TranslatorCredential(TRANSLATOR_KEY, API_REGION)
text_translator = TextTranslationClient(TRANSLATOR_ENDPOINT=TRANSLATOR_ENDPOINT, credential=credential)

def translate_text(input_text_elements, source_language, target_languages):
    try:
        response = text_translator.translate(
            content=input_text_elements,
            to=target_languages,
            from_parameter=source_language
        )
        translation = response[0] if response else None

        if translation:
            translated_texts = []
            for translated_text in translation.translations:
                translated_texts.append({
                    'target_language': translated_text.to,
                    'translated_text': translated_text.text
                })
            return translated_texts
        else:
            return []

    except Exception as e:
        print(f"Translation error: {e}")
        return []

source_language = "en"
target_languages = ["ko", "it"]

result_list = []

for news_item in news_list:
    name = news_item['name']
    description = news_item['description']
    date_published = news_item['datePublished']
    url = news_item['url']
    provider = news_item['provider'][0]['name']
    # name을 번역
    name_translation = translate_text([InputTextItem(text=name)], source_language, target_languages)
    translated_name = name_translation[0]['translated_text'] if name_translation else name

    # description을 번역
    description_translation = translate_text([InputTextItem(text=description)], source_language, target_languages)
    translated_description = description_translation[0]['translated_text'] if description_translation else description
    result_list.append({'name': name, 'description': description, 'datePublished': date_published, 'url': url, 'provider': provider, 'description_trans': translated_description, 'name_trans': translated_name})

# 결과 출력
for item in result_list:
    print(f"Name: {item['name']}")
    print(f"Description: {item['description']}")
    print(f"Date Published: {item['datePublished']}")
    print(f"URL: {item['url']}")
    print(f"description_trans: {item['description_trans']}")
    print(f"name_trans: {item['name_trans']}")
    print(f"provider: {item['provider']}")
    print()

for result in result_list:
    url = result['url']
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    text = soup.find('body').get_text().strip()
    cleaned_text = ' '.join(text.split('\n'))
    cleaned_text = ' '.join(text.split())
    # print(cleaned_text)
    # if len is more than 10, then can count it
    # print(cleaned_text)
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
        formatted_summary = re.sub(html_tag_pattern, '', news_item['description_trans'])
        url = news_item['url']
        news_dt = news_item['datePublished'].split('T')[0]
        source = news_item['provider']
        title_mt = re.sub(html_tag_pattern, '', news_item['name_trans'])
        send_news(now, keyword, news_dt, source, title, title_mt, formatted_summary, url, rel)
    

    #narajangteo(1,2,3,4,5,6,7,8,9)