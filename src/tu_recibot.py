#!/usr/bin/python3
# -*- coding: utf-8 -*-

import requests
import json
import logging
import sys
import re
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] (%(module)s:%(lineno)d) %(message)s')
logging.getLogger('requests').setLevel(logging.ERROR)

FOLDERS_PATTERN = re.compile('\/folders/([0-9]{1,3})\/documents', re.IGNORECASE)

BODY_PATTERN = re.compile('<ul class="dropdown-menu"[\s\S]*?<\/ul>')


def main():
    check_parameters()
    dni = sys.argv[1]
    password = sys.argv[2]
    site = sys.argv[3]
    process(dni, password, site)


def process(dni, password, site):
    session = login(dni, password, site)
    companies = get_companies(session, site)
    for company in companies:
        files = get_documents(session, site)
        download_files(session, files, company, site)
        logging.info("Finished downloading files for {}".format(company))
        change_company(session, site, companies)


def get_companies(session, site):
    pag_url = bandeja_url(site)
    response = get(pag_url, cookies=session, headers=headers(session))
    body = BODY_PATTERN.findall(response.text)
    patter_company = re.compile('<b>([\w ]*?)<\/b>')
    names = patter_company.findall(body[0])

    return names


def change_company(session, site, companies):
    if len(companies) > 1:
        get(change_company_url(site), cookies=session, headers=headers(session))


def get_documents(session, site) -> list:
    documents = []
    for category in get_categories(session, site):
        logging.info("Collecting files for category: {}".format(category))
        docs_left = True
        pag = 1
        while docs_left:
            docs = get_docs_for_page(pag, category, session, site)
            documents += docs
            docs_left = len(docs) > 0
            pag += 1
    return documents


def get_categories(session, site) -> set:
    pag_url = bandeja_url(site)
    response = get(pag_url, cookies=session, headers=headers(session))
    return parse_categories(response.text)


def get_docs_for_page(page: int, category, session, site) -> list:
    pag_url = files_paginated_url(page, category, site)
    response = post(pag_url, data='reload=1', headers=headers(session))
    res_dic = json.loads(response.text)
    return parse_documents(res_dic)


def download_files(session, files: list, company: str, site: str):
    logging.info("Downloading {} files for company {}...".format(len(files), company))
    create_download_folder()
    for doc in files:
        download_file(session, doc, company, site)


def login(dni, password, site):
    logging.info("Login...")
    response1 = post(cookies_url(site))
    response2 = post(login_url(site), data="login=1&usuario={}&clave={}".format(dni, password), allow_redirects=True,
                     headers=headers(response1.cookies))
    cookies = cookies_from_response(response2)
    assert len(cookies) > 0, "Error login in, impossible to get cookies"
    logging.info("Login OK")
    return cookies


def cookies_from_response(r):
    return r.history[0].cookies


def parse_documents(json_doc: dict) -> list:
    try:
        docs = json_doc["categorias"]["documentos"]
        return docs
    except Exception as e:
        logging.error("Unexpected error:", sys.exc_info()[0])
        return []


def parse_categories(html: str) -> set:
    categories = FOLDERS_PATTERN.findall(html)
    return set(categories)


def create_download_folder():
    if not os.path.exists("./docs"):
        os.makedirs("./docs")


def download_file(cookie_jar, doc, company, site):
    logging.info("Downloading document: {}".format(get_file_name(doc, company)))
    r = get(file_download_url(site, doc), stream=True, headers=headers(cookie_jar))
    if r is not None:
        with open(get_file_name(doc, company), 'wb') as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)


def get_file_name(doc, company):
    month, year = doc['periodo'].split("/")
    return "./docs/" + "{}-{}-{}-{}.pdf".format(year, month, company, doc['tipo_nombre']).replace(" ", "-")


def change_company_url(site):
    return url(site)['change_company']


def cookies_url(site):
    return url(site)['first_request']


def login_url(site):
    return url(site)['login']


def file_download_url(site, doc):
    return url(site)['file_download'].format(doc['id'])


def files_paginated_url(page: int, category: int, site: str):
    return url(site)['files_paginated'].format(category, page, category)


def bandeja_url(site: str):
    return url(site)['categories']


def headers(cookie_jar):
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": "PHPSESSID={}; AWSELB={}".format(cookie_jar.get("PHPSESSID"), cookie_jar.get("AWSELB"))
    }


def url(site):
    return {
        'change_company': 'https://{}.turecibo.com.ar/index.php?chu=1'.format(site),
        'first_request': 'http://www.{site}.turecibo.com/login.php'.replace("{site}", site),
        'login': 'https://{site}.turecibo.com/login.php'.replace("{site}", site),
        'categories': 'https://{site}.turecibo.com/bandeja.php'.replace("{site}", site),
        'files_paginated': 'https://{site}.turecibo.com.ar/bandeja.php?apiendpoint=/folders/{}/documents/available?pagination_5,{},2&folder={}&idactivo=null'.replace(
            "{site}", site),
        'file_download': 'https://{site}.turecibo.com/file.php?idapp=278&id={}&bandeja=yes'.replace("{site}", site)
    }


def post(url, data=None, **kwargs):
    response = requests.post(url, data=data, **kwargs)
    return handle_response('POST', url, data, response)


def get(url, **kwargs):
    response = requests.get(url, **kwargs)
    return handle_response('GET', url, None, response)


def check_parameters():
    if len(sys.argv) < 3:
        print("Usage:   python mi_recibot.py <<dni>> <<password>> <<site>> \n"
              "Example: python mi_recibot.py 23817653 swordfish oracle")
        sys.exit(-1)


def handle_response(method, url, payload, response):
    if response.status_code != 200:
        logging.error("Error in {} method to {} - Payload {}".format(method, url, payload))
        return None
    else:
        return response


if __name__ == "__main__":
    main()
