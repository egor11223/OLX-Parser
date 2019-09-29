# -*- coding: utf8 -*-
import requests
from bs4 import BeautifulSoup as bs
import csv
import datetime
import sqlite3

headers = {
    "accept": "*/*",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36 OPR/60.0.3255.170"
}
# Укажите токен телеграм
telegram_token = None

# Укажите чат id в который необходимо отправлять данные
telegram_chat_id = None

#Укажите URL для парсинга, так-же укажите все необходимые фильтры если необходимо
base_url = 'https://www.olx.ua/nedvizhimost/kvartiry-komnaty/arenda-kvartir-komnat/zaporozhe/?search%5Bfilter_float_price%3Ato%5D=4000&search%5Bdistrict_id%5D=47'

base_url_telegram = 'https://api.telegram.org/'+telegram_token+'/sendMessage'

conn = sqlite3.connect('ads.db')
cursor = conn.cursor()

def olx_parse(base_url, headers):
    global start
    start = datetime.datetime.now()
    urls = []
    urls.append(base_url)
    ads = []
    #использую сессию
    session = requests.Session()
    request = session.get(base_url, headers=headers)
    #проверка ответа от сервера
    if request.status_code == 200:
        soup = bs(request.content, "lxml")
        try:
            #определение последней страницы
            last_page = soup.find('a', attrs={'data-cy': 'page-link-last'})['href']
            num = list(last_page)
            number_of_last_page = str(num[-2])+str(num[-1])
            #итерация по всем страницам
            for i in range(int(number_of_last_page)-1):
                url = f'{base_url}&page={i+2}' #первая страница соответствует базовому "base_url",а страницы с "page=0" не существует, поэтому отсчет начинается с "page=2"
                #добавление URL всех страниц в список
                if url not in urls:
                    urls.append(url)
        except:
            pass

        #итерация по всем страницам
        for url in urls:
            request = session.get(url, headers=headers)
            soup = bs(request.content, 'lxml')
            trs = soup.find_all('tr', attrs={'class': 'wrap'}) #поиск всех классов с объявлениями
            #итерация по каждому объявлению
            for tr in trs:
                try:
                    #берем информацию о публикации обьявления
                    dateRecord = tr.find('td', attrs={'class': 'bottom-cell'}).find_all('small')[1].text
                    # забираем только сегодняшние обьявления
                    if dateRecord.find('Сегодня') >= 0:
	                    title = tr.find('a', attrs={'class': 'marginright5 link linkWithHash detailsLink'}).text
	                    href = tr.find('a', attrs={'class': 'marginright5 link linkWithHash detailsLink'})['href']
	                    price = tr.find('p', attrs={'class': 'price'}).text
	                    dataID = tr.find('table')['data-id']
	                    ads.append({
	                        'title': title,
	                        'url': href,
	                        'price': price,
	                        'id_ads': dataID,
	                        'date': dateRecord.strip()
	                    })


                except:
                    pass

    else:
        print('Error')
    end = datetime.datetime.now()
    print(f"Время выполнения парсинга: {end-start}")
    return ads



def send_to_db(id_ads, url, title, price, date):
	cursor.execute("INSERT INTO ads (id_ads, url, title, price, date) VALUES (?,?,?,?,?)", (id_ads, url, title, price, date))
	conn.commit()

def process_send(ads):
    for ad in ads:
        elem_exists = check_item_db(ad['id_ads'])
        # проверяем есть ли данный элемент в БД
        if not elem_exists:
            # Отправка в БД
            send_to_db(ad['id_ads'], ad['url'], ad['title'], ad['price'], ad['date'])
            # Отправка в телеграм
            send_telegram(ad['url'], ad['title'], ad['price'], ad['date'])

def check_item_db(id_ads):
    sql = 'SELECT * FROM ads WHERE id_ads=?'
    cursor.execute(sql, [(int(id_ads))])
    return cursor.fetchone()

def send_telegram(title, url, price, date):
    params = {'chat_id': telegram_chat_id,'text': title+'\n'+url+'\n'+price+'\n'+date}
    session = requests.Session()
    response = session.get(base_url_telegram, params=params)

ads = olx_parse(base_url, headers)
process_send(ads)