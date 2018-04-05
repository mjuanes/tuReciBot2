import requests
import json
import sys


class Document:
    def __init__(self, id, period, type, signed, ticket):
        self.id = id
        self.period = period
        self.type = type
        self.signed = signed
        self.ticket = ticket

    def __str__(self):
        return "id->" + str(self.id) + ",period->" + self.period + ",type->" + self.type + ",signed->" + str(
            self.signed) + ",ticket->" + str(self.ticket) + "\n"


login_url = "https://www.turecibo.com.ar/login.php?ref=Lw%3D%3D"
#list_url = "https://www.turecibo.com.ar/bandeja.php"
list_url = "https://www.despegar.turecibo.com.ar/bandeja.php?pag=1&category=1&idactivo=null"
session_cookie = "PHPSESSID"


def doLogin(dni, password):
    re = requests.post("https://www.turecibo.com.ar/login.php")

    url = "https://www.turecibo.com.ar/login.php"
    cookie = "PHPSESSID={}; AWSELB={}".format(re.cookies.get_dict().get("PHPSESSID"), re.cookies.get_dict().get("AWSELB"))
    # /*, headers={"Cookie": cookie}*/

    headers = {
        "Cookie": cookie,
        "Origin": "https://www.turecibo.com.ar",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Cache-Control": "max-age=0",
        "Referer": "https://www.turecibo.com.ar/login.php",
        "Connection": "keep-alive"
                      }

    r = requests.post(url, data="login=1&usuario={}&clave={}".format(dni, password), allow_redirects=True, headers=headers)
    r = r.history[0]
    print("Login response status code: {}".format(r.status_code))
    print("Cookie header" + "PHPSESSID={}; AWSELB={}".format(r.cookies.get("PHPSESSID"), r.cookies.get("AWSELB")))
    return r.cookies


def parseDocuments(jDocs):
    documents = []
    documentsSize = len(jDocs["documentosFirmables"])
    for x in range(0, documentsSize):
        jDoc = jDocs["documentosFirmables"][x]
        id = jDoc["id"]
        if (jDocs["tikets"].has_key(str(id))):
            ticket = jDocs["tikets"][str(id)]
        else:
            ticket = None

        doc = Document(jDoc["id"], jDoc["periodo"], jDoc["tipo"], jDoc["firmado"], ticket)
        documents.append(doc)
    return documents


def doList2(session):
    payload = "reload=1"
    cookie = "PHPSESSID={}; AWSELB={}".format(session.get("PHPSESSID"), session.get("AWSELB"))
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
               "Content-Length": str(len(payload))}
    response = requests.post(list_url, cookies={"Cookie": cookie},  data=payload)
    print(response.text)


def doList(session):
    jar = requests.cookies.RequestsCookieJar()
    jar.set(session_cookie, session, domain='ar.turecibo.com', path='/')
    payload = "reload=1"
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
               "Content-Length": str(len(payload))}
    i = 0
    totalSize = None
    while (totalSize == None or i < totalSize):
        i = i + 1
        response = requests.post(list_url, params={'pag': i}, data=payload, cookies=jar, headers=headers)
        jDocs = json.loads(response.text)
        totalSize = jDocs["totalPages"]
        docs = parseDocuments(jDocs)
        for doc in docs:
            print("Downloading " + doc.period + " " + doc.type)
            if (doc.ticket != None):
                downloadFile(doc, jar)


def downloadFile(doc, jar):
    r = requests.get("https://ar.turecibo.com/file.php?idapp=305&id=" + str(doc.id) + "&t=" + doc.ticket,
                     cookies=jar, stream=True)

    if r.status_code == 200:
        with open(doc.period.replace("/", "-") + "-" + doc.type + ".pdf", 'wb') as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)


def main():
    # if (len(sys.argv) != 3):
    #     print "python mi_recibot.py <<dni>> <<password>>"
    #     return

    dni = sys.argv[1]
    password = sys.argv[2]
    session = doLogin(dni, password)
    doList2(session)


if __name__ == "__main__":
    main()
