from bs4 import BeautifulSoup
import urllib3
import re

http = urllib3.PoolManager()

def getpage(url):
    try:
        request = http.request("GET",url)
        return request.data
    except urllib3.exceptions.HTTPError:
        print("error")
    return ""

def getshops(soup):

    for shop in soup.find_all("td", {"valign":"top", "width":"30%"}):
        details = [x.strip() for x in str(shop.a.contents).split('<br>')]
        shop_name = details[0]
        shop_name = shop_name[details[0].index("\\r\\n\\r\\n\\t\\t\\t\\t\\t\\t\\t") + len("\\r\\n\\r\\n\\t\\t\\t\\t\\t\\t\\t"):-2]
        print(shop_name) #naam
        print(details[1]) #straat + nr
        print(details[2]) #postcode + gemeente
        print(details[3][:details[3].index("<br/>")]) #provincie

    for desc in soup.find_all("td", {"valign":"top", "class":"normal", "colspan":"5"}):
        print(re.findall(r'\d+', desc.contents[0])[0]) #%res
        print(desc.b.text) #categorie
        print(re.findall(r'\d+', desc))

def main():
    print("main")

    soup = BeautifulSoup(getpage("http://www.resplus.be/nl/index.asp?name=&keyword=&contact=&city=tienen&radius=5&ps_guide=&province=&pagelanguage=1&pid=..%2Fnbs%2Fclients")
                         , 'html.parser')

    getshops(soup)


if __name__ == '__main__':
    main()
