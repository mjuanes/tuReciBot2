#!/usr/bin/python3
# -*- coding: utf-8 -*-

import requests
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] (%(module)s:%(lineno)d) %(message)s')


def main():
    if len(sys.argv) < 3:
        print("python mi_recibot.py <<dni>> <<password>>")
        return
    dni = sys.argv[1]
    password = sys.argv[2]
    company = get_parameter(sys.argv, 3)
    session = login(company, dni, password)
    files = get_documents(company, session)
    download_files(company, session, files)
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


def get_documents(company: str, session)-> list:
    documents = []
    for category in get_categories(company, session):
        logging.info("Collecting files for category: {}".format(category.name))
        docs_left = True
        pag = 1
        while docs_left:
            docs = get_docs_for_page(company, pag, category, session)
            documents += docs
            docs_left = len(docs) > 0
            pag += 1
    return documents


def get_categories(company: str, session) -> list:
    pag_url = files_paginated_url(1, 1)
    response = post(pag_url, cookies=session, data='reload=1', headers=headers(session))
    res_dic = json.loads(response.text)
    return parse_categories(res_dic)


def get_docs_for_page(page: int, category: Category, session) ->list:
    pag_url = files_paginated_url(page, category.id)
    response = post(pag_url, data='reload=1', headers=headers(session))
    res_dic = json.loads(response.text)
    return parse_documents(res_dic, category)


def download_files(session, files: list):
    for doc in files:
        download_file(doc, session)


def login(dni, password):
    logging.info("Login...")
    re = post(login_url())
    r = post(login_url(), data="login=1&usuario={}&clave={}".format(dni, password), allow_redirects=True, headers=headers(re.cookies))
    assert len(r.history) > 0, "Error getting cookies"
    r = r.history[0]
    logging.info("Login OK")
    return r.cookies


def parse_documents(json_doc: dict, category: Category) -> list:
    documents = []
    for doc in json_doc["documentosFirmables"]:
        ticket = json_doc["tikets"][str(doc["id"])]
        doc = Document(doc["id"], doc["periodo"], doc["tipo"], category, doc["firmado"], ticket)
        documents.append(doc)
    return documents


def parse_categories(dic: dict) -> list:
    categories = []
    for dic_cat in dic['categorias'].values():
        category = Category(dic_cat['id_categoria_tipo'], dic_cat['name'], dic_cat['totalDocumentos'], dic_cat['sinFirmar'])
        categories.append(category)
    return categories


def download_file(doc: Document, cookie_jar):
    logging.info("Downloading document: {}".format(doc))
    r = requests.get(file_download_url(doc), stream=True, headers=headers(cookie_jar))
    if r.status_code == 200:
        with open("{}-{}.pdf".format(doc.period.replace("/", "-"), doc.type), 'wb') as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)
    else:
        logging.error("Error downloading file")


def login_url():
    return "https://www.turecibo.com.ar/login.php"


def file_download_url(doc: Document):
    return "https://ar.turecibo.com/file.php?idapp=305&id={}&t={}".format(doc.id, doc.ticket)


def files_paginated_url(company: str, page: int, category: int):
    url(company)
    return 'https://www.turecibo.com.ar/bandeja.php?pag={}&category={}&idactivo=null'.format(page, category)


def headers(cookie_jar):
    return {
    "Content-Type": "application/x-www-form-urlencoded",
    "Cookie": "PHPSESSID={}; AWSELB={}".format(cookie_jar.get("PHPSESSID"), cookie_jar.get("AWSELB"))
    }


def url(company: str):
    if company is None:
        return {
                'first_request': 'https://www.turecibo.com.ar/login.php',
                'login': 'https://www.turecibo.com.ar/login.php',
                'files_paginated': 'https://www.turecibo.com.ar/bandeja.php?pag={}&category={}&idactivo=null',
                'file_download': 'https://www.turecibo.com.ar/bandeja.php?pag={}&category={}&idactivo=null'
            }
    else:
        return {
            'first_request': 'http://www.{}.turecibo.com/login.php'.format(company),
            'login': 'https://{}.turecibo.com/login.php',
            'files_paginated': 'https://{}.turecibo.com/bandeja.php?pag={}&category={}&idactivo=null',
            'file_download': 'https://{}.turecibo.com/file.php?idapp=305&id={}&t={}'
        }

def post(url, data=None, **kwargs):
    logging.info("Hitting {}".format(url))
    response = requests.post(url, data=data, **kwargs)
    if response.status_code != 200:
        logging.error("Error in post")
        return None
    else:
        return response


def get_parameter(args, order: int):
    try:
        return args[order]
    except IndexError:
        return None


if __name__ == "__main__":
    main()
