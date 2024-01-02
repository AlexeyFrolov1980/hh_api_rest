import requests  # Для запросов по API
import json  # Для обработки полученных результатов
import time  # Для задержки между запросами
import os  # Для работы с файлами
import pprint
import list_with_counter
import sqlite3
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base


def get_areas():
    with requests.get('https://api.hh.ru/areas') as req:
        data = req.content.decode()

    jsobj = json.loads(data)
    areas = []
    for k in jsobj:
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


def fill_araas_table(cnn: sqlite3.Connection):
    areas = get_areas()
    cursor = cnn.cursor()
    for a in areas:
        area_id = a[0]
        area_name = a[1]
        city_id = a[2]
        city_name = a[3]
        params = {'area_id': area_id, 'area_name': area_name, 'city_id': city_id, 'city_name': city_name}

        SQL = "SELECT * FROM Cities WHERE CityId=:city_id"
        cursor.execute(SQL, {"city_id": city_id})
        city = cursor.fetchone()

        if city is None:
            SQL = "INSERT INTO Cities (AreaId, AreaName, CityID, CityName) VALUES (:area_id, :area_name, :city_id, :city_name)"
        else:
            SQL = "UPDATE Cities SET AreaId=:area_id, AreaName=:area_name, CityId=:city_id, CityName=:city_name WHERE CityId=:city_id"

        cursor.execute(SQL, params)


def save_vacancies_to_db(cnn: sqlite3.Connection, vac: list):
    cursor = cnn.cursor()
    for v in vac:
        params = {"ID": v[0],
                  "Name": v[1],
                  "cityID": v[5],
                  "Sallary": v[3],
                  "SallaryCur": v[2],
                  "PublishDate": v[6],
                  "URL": v[4]}

        SQL = "SELECT * FROM vacancies WHERE ID=:ID"
        cursor.execute(SQL, params)
        if cursor.fetchone() is None:
            SQL = "INSERT INTO vacancies (ID, Name, cityID, Sallary, SallaryCur ,PublishDate, URL) "
            SQL += "VALUES (:ID, :Name, :cityID, :Sallary, :SallaryCur ,:PublishDate, :URL)"
        cursor.execute(SQL, params)


def get_vacancies_from_DB (cnn: sqlite3.Connection, keyword:str, city_id: int):
    cursor = cnn.cursor()
    SQL = "select  ID, Name, Sallary, SallaryCur, URL, CityName, PublishDate "
    SQL += "from vacancies join Cities on vacancies.cityID = Cities.CityID "
    SQL += "WHERE Name like '%" + keyword + "%' and (Cities.cityID = :city_id or Cities.AreaID = :city_id)"

    params = {"city_id": city_id}
    cursor.execute(SQL, params)
    return cursor.fetchall()


def get_area_code(area_name):
    areas = get_areas()
    for a in areas:
        if a[1].lower() == area_name.lower():
            return int(a[0])
        if a[3].lower() == area_name.lower():
            return int(a[2])
    return -1


def get_area_code_from_vac(vac):
    return vac['area']['id']


def sallary_to_txt(currency, sal):
    if (not currency is None) and (not sal is None):
        return str(sal) + "  " + currency
    else:
        return "Не указана"


def get_sallary(vacancy):
    # print(vac)
    sal_txt = vacancy['salary']
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


def make_params(ketwords, area_code):
    params = {
        'text': 'NAME:' + ketwords,  # Текст фильтра. В имени должно быть слово "Аналитик"
        'area': area_code,  # Поиск ощуществляется по вакансиям города Москва
        'page': 0,  # Индекс страницы поиска на HH
        'per_page': 100  # Кол-во вакансий на 1 странице
    }
    return params


def calc_mean_sallary_rub(sallaries, count):
    usd_to_rub = 91.64
    eur_to_rub = 98.4

    mean_sallary = 0
    print(sallaries)

    for key, value in sallaries.list_items.items():
        if key == 'RUR':
            mean_sallary += value

        if key == 'USD':
            mean_sallary += value * usd_to_rub

        if key == 'EUR':
            mean_sallary += value * eur_to_rub

    if count > 0:
        return mean_sallary / count
    else:
        return 0


def get_stat(params, requirments_count=-1):
    # Собираем требования
    requirements = list_with_counter.list_with_counter()

    # Собираем зарплаты в валютах
    sallaries = list_with_counter.list_with_counter()

    # Счетчик не пустых зарплат по каждой валюте
    not_zero_sallaries = list_with_counter.list_with_counter()

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

        # time.sleep(0.25)
        print('Cтраница: ', concurrent_page + 1, ' из ', v_pages + 1, ' обработана')
        concurrent_page += 1

    requirements.sort_by_value()

    # Считаем % от требований

    # Считаем среднюю ЗП

    mean_sallary = calc_mean_sallary_rub(sallaries, sum(not_zero_sallaries.list_items.values()))

    # Собираем большой словарь для записи в json
    if requirments_count == -1:
        result = {'params': params,
                  'mean_sallary': mean_sallary,
                  'requirements': requirements.calc_percentage().list_items}
    else:
        result = {'params': params,
                  'mean_sallary': mean_sallary,
                  'requirements': requirements.calc_percentage().get_top(requirments_count)}

    return result


def stat_structure_to_str(stat_stucture):
    res = 'Средняя зарплата ' + str(stat_stucture['mean_sallary']) + " руб. \n"

    res += 'Основные ТОР ' + str(len(stat_stucture['requirements'])) + " требований \n"
    for key, value in stat_stucture['requirements'].items():
        res += str(key) + " " + str(value) + "% \n"

    return res


def get_vac_list(params, per_page=50, page=0):
    params['page'] = page
    params['per_page'] = per_page
    data = get_page(params, page)
    jsObj = json.loads(data)
    v_pages = jsObj['pages']
    # Необязательная задержка, но чтобы не нагружать сервисы hh, оставим. 5 сек мы может подождать
    vlst = jsObj['items']
    res = list()

    for vac in vlst:
        cur, sal = get_sallary(vac)
        res.append([vac['id'], vac['name'], cur, sal,
                    vac['apply_alternate_url'], get_area_code_from_vac(vac), vac['published_at']])

    print(res)
    return res
