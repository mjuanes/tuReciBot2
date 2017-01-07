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


login_url = "https://ar.turecibo.com/login.php?ref=%2Fbandeja.php"
list_url = "https://ar.turecibo.com/bandeja.php"
session_cookie = "PHPSESSID"


def doLogin(dni, password):
    r = requests.post(login_url, data={'login': '1', 'usuario': dni, 'clave': password},
                      allow_redirects=False)
    print(r.status_code)
    return r.cookies[session_cookie]


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
        jDocs = json.loads(requests.post(list_url, params={'pag': i}, data=payload, cookies=jar, headers=headers).text)
        totalSize = jDocs["totalPages"]
        docs = parseDocuments(jDocs)
        for doc in docs:
            print "Downloading " + doc.period + " " + doc.type
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
    if (len(sys.argv) != 3):
        print "python mi_recibot.py <<dni>> <<password>>"
        return

    dni = sys.argv[1]
    password = sys.argv[2]
    session = doLogin(dni, password)
    doList(session)


if __name__ == "__main__":
    main()
