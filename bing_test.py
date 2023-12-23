import requests
from decouple import config
from bs4 import BeautifulSoup
from collections import Counter


subscription_key = config('subscription_key', default='')

print(subscription_key)

search_url = "https://api.bing.microsoft.com/v7.0/search"

search_term = "2023 December 20th the Times news about distribution, logistics, trade, crude oil"

headers = {"Ocp-Apim-Subscription-Key": subscription_key}
params = {"q": search_term, "textDecorations": True, "textFormat": "HTML"}
response = requests.get(search_url, headers=headers, params=params)
response.raise_for_status()
search_results = response.json()
pages = search_results['webPages']
results = pages['value']

name_date = []
for item in results:
    name = item['name']
    date_published = item['datePublished']
    name_date.append({'name': name, 'datePublished': date_published})

# 추출된 결과 출력
print(name_date)

# request to the result page that we get from the bing api
for result in results[:10]:
    response = requests.get(result['url'])
    soup = BeautifulSoup(response.content, 'html.parser')
    text = soup.find('body').get_text().strip()
    cleaned_text = ' '.join(text.split('\n'))
    cleaned_text = ' '.join(text.split())
    # if len is more than 10, then can count it
    # print(cleaned_text)
    counter = Counter(x for x in cleaned_text.split() if len(x) > 5)
    # find most common elements top 10
    elements_top10 = counter.most_common(10)
    # print(elements_top10)
    # # html data
    # content = response.content
    # print(content)
    break
