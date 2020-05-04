import requests
import csv
import os
import locale
import re
import time
from bs4 import BeautifulSoup
from datetime import date
from datetime import datetime
from multiprocessing import Pool


def get_html(url):
    r = requests.get(url)
    return r.text


def get_total_pages(html):
    soup = BeautifulSoup(html, 'lxml')
    pages = soup.find('nav', class_='paginator-public').find_all('a', class_='paginator-page-btn')
    total_pages = pages[-2].get('data-page')
    return int(total_pages)


def get_parameter(parameters, attribute):
    _param = parameters.find('dt', {"data-name": attribute})
    if _param:
        return _param.find_next_sibling("dd").text
    else:
        return ''


def get_complex(parameters):
    _param = parameters.find('dt', {"data-name": "map.complex"})
    if not _param:
        return ''
    elif _param.find_next_sibling("dd").a:
        return _param.find_next_sibling("dd").a.text
    else:
        return _param.find_next_sibling("dd").text


def get_page_data(html, csv_file):
    soup = BeautifulSoup(html, 'lxml')
    flats = soup.find('section', class_='a-list').find_all('div', class_='a-card')
    for flat in flats:
        id = flat.get('data-id')
        inner_html = get_html(f"https://krisha.kz/a/show/{id}")
        inner_soup = BeautifulSoup(inner_html, 'lxml')
        # helpers
        _description = flat.find('div', class_='a-card__descr')
        #_title = _description.find('div', 'a-title').a.get('title')
        _title = _description.find('a', class_='a-card__title').get_text()
        #_status = _description.find_all('div', 'a-status-side-wrapper')[-1]
        _status = _description.find_all('div', 'card-stats__item')
        _date = _status[1].get_text().strip().replace('.','')
        #_comment = _status.find('span', 'a-comment-count')
        _location = re.search('{"lat":(\d*\.\d*),"lon":(\d*\.\d*)', inner_soup.head.script.text)
        _json_view = requests.get(f"https://krisha.kz/ms/views/krisha/live/{id}/")
        #_parameters = inner_soup.find('dl', class_='a-parameters')
        _parameters = inner_soup.find('div', class_='offer__parameters')
        _building = get_parameter(_parameters, "flat.building")
        _re_building = re.search('([а-я]+)?,?\s?((\d+) г.п.)?', _building)
        _floors = get_parameter(_parameters, "flat.floor")
        _re_floors = re.search('(\d+)( из (\d+))?', _floors)
        _area = get_parameter(_parameters, "live.square")
        _re_area = re.search('(\d+\.?\d?) м2(, жилая — (\d+\.?\d?) м2)?(, кухня — (\d+\.?\d?) м2)?', _area)
        # features in order of columns
        # date = datetime.strptime(_date, '%d %b').replace(year=2018).strftime('%d.%m.%Y')
        date = _date
        #city = inner_soup.find('div', class_="a-where-region").text
        city = _status[0].get_text()
        #address = _title.split(', ')[-1]
        address = _description.find('div', class_='a-card__subtitle').get_text().replace('\n', '').strip()
        lat, lon = [_location.group(1), _location.group(2)] if _location else ['', '']
        price = inner_soup.find('div', class_='offer__price').text.replace('\n', '').replace(' ', '').replace('₸','').strip()
        try:
            view_count = _json_view.json()["data"][f"{id}"]["nb_views"]
        except:
            view_count = 0
        room_count = _title.split('-')[0]
        image_count = flat.find('a', class_='a-card__image').get('data-nb')
        #comment_count = _comment.a.get_text().split(' ')[0] if _comment else 0
        color = flat.get('data-color')
        is_owner = 1 if _description.find('div', 'user-owner') else 0
        #is_urgent = 1 if _description.find('span', 'a-label--red') else 0
        building_type = _re_building.group(1) or ''
        building_year = _re_building.group(3) or ''
        floor = (_re_floors.group(1) or '') if _re_floors else ''
        building_floors = (_re_floors.group(3) or '') if _re_floors else ''
        area_total = (_re_area.group(1) or '') if _re_area else ''
        area_living = (_re_area.group(3) or '') if _re_area else ''
        area_kitchen = (_re_area.group(5) or '') if _re_area else ''
        renovation = get_parameter(_parameters, "flat.renovation")
        toilet = get_parameter(_parameters, "flat.toilet")
        balcony = get_parameter(_parameters, "flat.balcony")
        balcony_glass = get_parameter(_parameters, "flat.balcony_g")
        door = get_parameter(_parameters, "flat.door")
        phone = get_parameter(_parameters, "flat.phone")
        inet_type = get_parameter(_parameters, "inet.type")
        furniture = get_parameter(_parameters, "live.furniture")
        floor_type = get_parameter(_parameters, "flat.flooring")
        security = get_parameter(_parameters, "flat.security")
        priv_dorm = get_parameter(_parameters, "flat.priv_dorm")
        parking = get_parameter(_parameters, "flat.parking")
        room_height = get_parameter(_parameters, "ceiling")[:3]
        complex = get_complex(_parameters)
        #is_pledged = 1 if inner_soup.find('div', class_='a-is-mortgaged') else 0
        csv_file.writerow([id, date, city, address, lat, lon, price, view_count, room_count, image_count,
                           color, is_owner,
                           building_type, building_year, floor, building_floors, area_total, area_living, area_kitchen,
                           renovation, toilet, balcony, balcony_glass, door, phone, inet_type, furniture, floor_type,
                           security, priv_dorm, parking, room_height, complex])


def parsing(csv_name, city, page):
    with open(csv_name, 'a', encoding='utf-8', newline='') as csv_file:
        csv_file = csv.writer(csv_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        page_url = f'https://krisha.kz/prodazha/kvartiry/{city}/?page={page}'
        time.sleep(0.01)
        page_html = get_html(page_url)
        get_page_data(page_html, csv_file)
        print(city, page, "parsed")


def main():
    # set locale to make datatime work
    locale.setlocale(locale.LC_ALL, ('RU', 'UTF8'))
    cities = ['ust-kamenogorsk', 'astana', 'almaty']
    for city in cities:
        today = date.today().strftime("%d.%m.%Y")
        base_url = f'https://krisha.kz/prodazha/kvartiry/{city}/'
        html = get_html(base_url)
        total_pages = get_total_pages(html)
        file_name = os.path.join(os.path.dirname(__file__), f"redesign/{city}/{today}.csv")

        with open(file_name, 'w', encoding='utf-8', newline='') as csv_file:
            csv_file = csv.writer(csv_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            csv_file.writerow(['id', 'date', 'city', 'address', 'lat', 'lon', 'price', 'view_count', 'room_count',
                                'image_count', 'color', 'is_owner', 'building_type',
                                'building_year', 'floor', 'building_floors', 'area_total', 'area_living',
                                'area_kitchen', 'renovation', 'toilet', 'balcony', 'balcony_glass', 'door', 'phone',
                                'inet_type', 'furniture', 'floor_type', 'security', 'priv_dorm', 'parking',
                                'room_height', 'complex'])

        map_variables = tuple((file_name, city, page) for page in range(1, total_pages + 1))
        with Pool(40) as p:
            p.starmap(parsing, map_variables)

        print('\033[1m\033[95m' + f"{city} has been done!".upper() + '\033[0m')


if __name__ == '__main__':
    main()
