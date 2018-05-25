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

site = None
pattern = re.compile('\/folders/([0-9]{1,3})\/documents', re.IGNORECASE)


def main():
    if len(sys.argv) < 3:
        print("python mi_recibot.py <<dni>> <<password>>")
        return
    dni = sys.argv[1]
    password = sys.argv[2]
    site = sys.argv[3]
    session = login(dni, password, site)
    files = get_documents(session, site)
    download_files(session, files, site)
    logging.info("Finished")


class Document:
    def __init__(self, id, period, type, category, signed, ticket):
        self.id = id
        self.period = period
        self.type = type
        self.category = category
        self.signed = signed
        self.ticket = ticket

    def __str__(self):
        return "id: {}, period: {}, type: {}, category: {}".format(self.id, self.period, self.type, self.category.name)


class Category:
    def __init__(self, id, name, total, without_signed):
        self.id = id
        self.name = name
        self.total = total
        self.without_signed = without_signed

    def __str__(self):
        return "id: {}, name: {}".format(self.id, self.named)


def get_documents(session, site) -> list:
    documents = []
    for category in get_categories2(session, site):
        logging.info("Collecting files for category: {}".format(category))
        docs_left = True
        pag = 1
        while docs_left:
            docs = get_docs_for_page(pag, category, session, site)
            documents += docs
            docs_left = len(docs) > 0
            pag += 1
            return docs
    return documents


def get_categories(session, site) -> list:
    pag_url = files_paginated_url(1, 1, site)
    response = post(pag_url, cookies=session, data='reload=1', headers=headers(session))
    res_dic = json.loads(response.text)
    return parse_categories(res_dic)


def get_categories2(session, site) -> list:
    pag_url = bandeja_url(site)
    response = get(pag_url, cookies=session, headers=headers(session))
    return parse_categories2(response.text)


def get_docs_for_page(page: int, category, session, site) -> list:
    pag_url = files_paginated_url(page, category, site)
    response = post(pag_url, data='reload=1', headers=headers(session))
    res_dic = json.loads(response.text)
    return parse_documents2(res_dic, category)


def download_files(session, files: list, site: str):
    logging.info("Downloading {} files...".format(len(files)))
    create_download_folder()
    for doc in files:
        download_file(session, doc, site)


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


def parse_documents(json_doc: dict, category: Category) -> list:
    documents = []
    for doc in json_doc["documentosFirmables"]:
        ticket = json_doc["tikets"][str(doc["id"])]
        doc = Document(doc["id"], doc["periodo"], doc["tipo"], category, doc["firmado"], ticket)
        documents.append(doc)
    return documents


def parse_documents2(json_doc: dict, category: Category) -> list:
    try:
        docs = json_doc["categorias"]["documentos"]
        return docs
    except:
        return []


def parse_categories(dic: dict) -> list:
    categories = []
    for dic_cat in dic['categorias'].values():
        category = Category(dic_cat['id_categoria_tipo'], dic_cat['name'], dic_cat['totalDocumentos'],
                            dic_cat['sinFirmar'])
        categories.append(category)
    return categories


def parse_categories2(html: str) -> list:
    categories = pattern.findall(html)
    return set(categories)


def create_download_folder():
    if not os.path.exists("./docs"):
        os.makedirs("./docs")


def download_file(cookie_jar, doc, site):
    logging.info("Downloading document: {}".format(get_file_name(doc)))
    r = requests.get(file_download_url(site, doc), stream=True, headers=headers(cookie_jar))
    if r.status_code == 200:
        with open(get_file_name(doc), 'wb') as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)
    else:
        logging.error("Error downloading file")


def get_file_name(doc):
    month, year = doc['periodo'].split("/")
    return "./docs/" + "{}-{}-{}.pdf".format(year, month, doc['tipo_nombre'])


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
        'first_request': 'http://www.{site}.turecibo.com/login.php'.replace("{site}", site),
        'login': 'https://{site}.turecibo.com/login.php'.replace("{site}", site),
        'categories': 'https://{site}.turecibo.com/bandeja.php'.replace("{site}", site),
        'files_paginated': 'https://{site}.turecibo.com.ar/bandeja.php?apiendpoint=/folders/{}/documents/available?pagination_5,{},2&folder={}&idactivo=null'.replace(
            "{site}", site),
        'file_download': 'https://{site}.turecibo.com/file.php?idapp=278&id={}&bandeja=yes'.replace("{site}", site)
    }


def post(url, data=None, **kwargs):
    logging.info("Hitting {}".format(url))
    response = requests.post(url, data=data, **kwargs)
    if response.status_code != 200:
        logging.error("Error in post")
        return None
    else:
        return response


# A otra funcion el manejo de errores
def get(url, **kwargs):
    logging.info("Hitting {}".format(url))
    response = requests.get(url, **kwargs)
    if response.status_code != 200:
        logging.error("Error in get")
        return None
    else:
        return response


def get_parameter(args, order: int):
    try:
        return args[order]
    except IndexError:
        return None


def init_variables(args):
    global site
    site = get_parameter(args, 3)


if __name__ == "__main__":
    main()
