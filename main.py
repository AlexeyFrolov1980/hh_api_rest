import requests  # Для запросов по API
import json  # Для обработки полученных результатов
import time  # Для задержки между запросами
import os  # Для работы с файлами
import pprint
import list_with_counter


def get_areas():
    with requests.get('https://api.hh.ru/areas') as req:
        data = req.content.decode()

    jsObj = json.loads(data)
    areas = []
    for k in jsObj:
        for i in range(len(k['areas'])):
            if len(k['areas'][i]['areas']) != 0:  # Если у зоны есть внутренние зоны
                for j in range(len(k['areas'][i]['areas'])):
                    areas.append([k['id'],
                                  k['name'],
                                  k['areas'][i]['areas'][j]['id'],
                                  k['areas'][i]['areas'][j]['name']])
            else:  # Если у зоны нет внутренних зон
                areas.append([k['id'],
                              k['name'],
                              k['areas'][i]['id'],
                              k['areas'][i]['name']])
    return areas


def get_sallary(vacancy):
    # print(vac)
    sal_txt = vac['salary']
    if sal_txt is None:
        return None, None
    else:
        currency = sal_txt['currency']
        sal_from = sal_txt['from']
        sal_to = sal_txt['to']

    # print('currency: ', currency, '   ', type(currency))
    # print('sal_from: ', sal_from, '   ', type(sal_from))
    # print('sal_to: ', sal_to, '   ', type(sal_to))

    # Вычисляем среднюю ЗП
    if sal_from is not None:
        if sal_to is not None:
            return currency, (sal_to - sal_from) / 2.0
        else:
            return currency, sal_from
    else:
        if sal_to is not None:
            return currency, sal_to
        else:
            return currency, None


def get_requirements(vacancy):
    snip = vacancy['snippet']

    requirement = snip['requirement']

    # print(requirement)
    if requirement is None:
        return list()
    else:
        requirements = requirement.split(".")
        'Убираем лишние пробелы'
        for i in range(len(requirements)):
            requirements[i] = requirements[i].strip()
        return requirements


def get_page(params, page=0):
    # Справочник для параметров GET-запроса
    params['page'] = page,  # Индекс страницы поиска на HH

    with requests.get('https://api.hh.ru/vacancies', params) as req:  # Посылаем запрос к API
        data = req.content.decode()  # Декодируем его ответ, чтобы Кириллица отображалась корректно

    return data


# Собираем требования
requirements = list_with_counter.list_with_counter()

# Собираем зарплаты в валютах
sallaries = list_with_counter.list_with_counter()

# Счетчик не пустых зарплат по каждой валюте
not_zero_sallaries = list_with_counter.list_with_counter()

params = {
    'text': 'NAME:python',  # Текст фильтра. В имени должно быть слово "Аналитик"
    'area': 1,  # Поиск ощуществляется по вакансиям города Москва
    'page': 0,  # Индекс страницы поиска на HH
    'per_page': 100  # Кол-во вакансий на 1 странице
}

concurrent_page = 0
v_pages = 0
vacancies_count = 0

while concurrent_page <= v_pages:

    data = get_page(params, concurrent_page)

    # Преобразуем текст ответа запроса в справочник Python
    jsObj = json.loads(data)
    v_pages = jsObj['pages']
    # Необязательная задержка, но чтобы не нагружать сервисы hh, оставим. 5 сек мы может подождать
    vlst = jsObj['items']

    for vac in vlst:
        vacancies_count += 1
        currency, sallary = get_sallary(vac)
        sallaries.add_item(currency, sallary)
        not_zero_sallaries.add_item(currency)
        requirements.add_items(get_requirements(vac))

    #time.sleep(0.25)
    print('Cтраница: ', concurrent_page + 1, ' из ', v_pages + 1, ' обработана')
    concurrent_page += 1

requirements.sort_by_value()

#print(requirements)
#print(sallaries)
#print(not_zero_sallaries)
#print(vacancies_count)

# Считаем % от требований

#Считаем среднюю ЗП
usd_to_rub = 91.64
eur_to_rub =  98.4

mean_sallary = (sallaries['RUR'] + usd_to_rub*sallaries['USD']+eur_to_rub*sallaries['EUR'])/sum(not_zero_sallaries.list_items.values())

#Собираем большой словарь для записи в json

result = {'params': params,
          'mean_sallary' : mean_sallary,
          'requirements': requirements.calc_percentage().list_items}

#print(result)

with open('data.txt', 'w') as outfile:
    json.dump(result, outfile)