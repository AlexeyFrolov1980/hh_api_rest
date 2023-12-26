from flask import Flask, render_template, request
import hh_functions
import datetime
import sqlite3


debug_flag = True
DB_NAME = 'DB/hh.sqlite'
app = Flask(__name__)



#Получаем список регионов из hh для отображения в поиске. Делаем это 1 раз при старте для оптимизации
# (берем 20 первых)

def test_reg_list(count=50):
    res = [['113','Россия','113','Россия'], ['113','Россия','1', 'Москва'], ['113','Россия','2', 'Петербург']]
    return res + hh_functions.get_areas()[:count]


region_list = test_reg_list()

main_menu_items = {"Главная": "/",
                   "Поиск": "/form",
                   "Контакты": "/contacts"}


@app.route('/')
def index():
    return render_template('index.html',  nav_menu = main_menu_items)



@app.route('/contacts/')
def contacts():

    developer_name = 'Alexey'
    return render_template('contacts.html', developer_name=developer_name, nav_menu=main_menu_items, current_date = "2023-12-23")


@app.route('/form/', methods=['post', 'get'])
def showform():
    query_string = "Нет параметров запроса"
    regions = "Регионы не выбраны"
    vac_data=None
    params={}

    print(request)
    if request.method == 'GET':
        pass
        # запрос к данным формы
        regions = request.args.get('search_regions')
        query_string = request.args.get('query_string')

        reg_id = 113 #вся Россия
        if regions is not None:
           reg_id = int(regions)
        if query_string is None:
            query_string = ''


        #Парсим вакансии с hh и сохраняем их в БД
        if query_string != '' :
            params = hh_functions.make_params(query_string, reg_id)
            vac_data_hh = hh_functions.get_vac_list(params, per_page=50, page=0)

            conn = sqlite3.connect(DB_NAME)
            with conn:
                hh_functions.save_vacancies_to_db(conn, vac_data_hh)
                vac_data = hh_functions.get_vacancies_from_DB(conn, query_string, reg_id)

            print(vac_data_hh)
            print(vac_data)


    return render_template('form.html',  nav_menu=main_menu_items, query_str=query_string,
                           search_reg=regions, region_list=region_list, vac_data=vac_data)



if not debug_flag:
    #При запуске 1 раз загружаем или апдейтим справочник городов
    conn = sqlite3.connect(DB_NAME)
    with conn:
        hh_functions.fill_araas_table(conn)

if __name__ == "__main__":
    app.run(debug=True)