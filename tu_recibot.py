#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import re
import sys
import itertools
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] (%(module)s:%(lineno)d) %(message)s')
logging.getLogger('requests').setLevel(logging.ERROR)

FOLDERS_PATTERN = re.compile('\/folders/([0-9]{1,})\/documents', re.IGNORECASE)
COMPANY_PATTERN = re.compile('<b>([\w ]*?)<\/b>')
BODY_PATTERN = re.compile('<ul class="dropdown-menu"[\s\S]*?<\/ul>')


def main():
    dni, password, site = validate_and_get_parameters()
    download_for_user(dni, password, site)


def download_for_user(dni, password, site):
    session = login(dni, password, site)
    companies = get_companies(session, site)
    download_files_for_companies(session, site, companies)


def download_files_for_companies(session, site, companies):
    for company in companies:
        files = get_documents(session, site)
        download_files(session, files, company, site)
        logging.info("Finished downloading files for {}".format(company))
        change_company(session, site, companies)


def get_companies(session, site):
    pag_url = bandeja_url(site)
    response = get(pag_url, cookies=session, headers=build_headers(session))
    body = BODY_PATTERN.findall(response.text)
    companies_names = COMPANY_PATTERN.findall(body[0])
    logging.info("Companies fetched: {}".format(companies_names))

    return companies_names


def change_company(session, site, companies):
    if len(companies) > 1:
        get(change_company_url(site), cookies=session, headers=build_headers(session))


def get_documents(session, site) -> list:
    documents = []
    for category in get_categories(session, site):
        documents += get_documents_for_category(session, site, category)
    return documents


def get_documents_for_category(session, site, category) -> list:
    logging.info("Collecting files for category: {} ...".format(category))
    documents = []
    for docs_for_page in docs_pager_generator(category, session, site):
        documents += docs_for_page
    logging.info("{} files collected for category {}".format(len(documents), category))
    return documents


def docs_pager_generator(category, session, site):
    for page in itertools.count(start=1):
        docs_for_page = get_docs_for_page(page, category, session, site)
        if docs_for_page:
            yield docs_for_page
        else:
            return


def get_categories(session, site) -> set:
    pag_url = bandeja_url(site)
    response = get(pag_url, cookies=session, headers=build_headers(session))
    return parse_categories(response.text)


def get_docs_for_page(page: int, category, session, site) -> list:
    pag_url = files_paginated_url(page, category, site)
    response = post(pag_url, data='reload=1', headers=build_headers(session))
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
                     headers=build_headers(response1.cookies))
    cookies = cookies_from_response(response2)
    logging.info("Login OK")
    return cookies


def cookies_from_response(r):
    assert r is not None and len(r.history) > 0, "No cookies to fetch. Wrong username or password."
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
    response = get(file_download_url(site, doc), stream=True, headers=build_headers(cookie_jar))
    if response is not None:
        write_file(response, doc, company)


def write_file(response, doc, company):
    file_name = get_file_name(doc, company)
    with open(file_name, 'wb') as fd:
        for chunk in response.iter_content(chunk_size=128):
            fd.write(chunk)


def get_file_name(doc, company):
    month, year = doc['periodo'].split("/")
    tipo_doc = doc['tipo_nombre']

    path = "./docs/"
    file_name = "{}-{}-{}-{}$SUFIX.pdf".format(year, month, company, tipo_doc).replace(" ", "-")

    return modify_if_file_name_exists(path + file_name)


def modify_if_file_name_exists(file_name):
    name = file_name.replace("$SUFIX", "")
    sufix = 1
    while os.path.exists(name):
        sufix += 1
        name = file_name.replace("$SUFIX", "-" + str(sufix))

    return name


def change_company_url(site):
    return url_for_site(site)['change_company']


def cookies_url(site):
    return url_for_site(site)['first_request']


def login_url(site):
    return url_for_site(site)['login']


def file_download_url(site, doc):
    return url_for_site(site)['file_download'].format(doc['id'])


def files_paginated_url(page: int, category: int, site: str):
    return url_for_site(site)['files_paginated'].format(category, page, category)


def bandeja_url(site: str):
    return url_for_site(site)['categories']


def build_headers(cookie_jar):
    value_awsalb = cookie_jar.get("AWSALB")
    value_awselb = cookie_jar.get("AWSELB")
    key, value = ("AWSELB", value_awselb) if value_awselb is not None else ("AWSALB", value_awsalb)
    return {
        'Content-Type': "application/x-www-form-urlencoded",
        'Cookie': "PHPSESSID={}; {}={}".format(cookie_jar.get("PHPSESSID"), key, value)
    }



def url_for_site(site):
    return {
        'change_company': 'https://{}.turecibo.com.ar/index.php?chu=1'.format(site),
        'first_request': 'https://{site}.turecibo.com/login.php'.replace("{site}", site),
        'login': 'https://{site}.turecibo.com/login.php'.replace("{site}", site),
        'categories': 'https://{site}.turecibo.com.ar/bandeja.php'.replace("{site}", site),
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


def validate_and_get_parameters():
    if len(sys.argv) is not 4:
        print("Usage:   python mi_recibot.py <<dni>> <<password>> <<site>> \n"
              "Example: python mi_recibot.py 23817653 swordfish oracle")
        sys.exit(-1)
    else:
        return sys.argv[1], sys.argv[2], sys.argv[3]


def handle_response(method, url, payload, response):
    if response.status_code != 200:
        logging.error("Error in {} method to {} - Payload {}.".format(method, url, payload))
        return None
    else:
        return response


if __name__ == "__main__":
    main()
