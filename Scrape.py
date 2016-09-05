from bs4 import BeautifulSoup
import urllib3
import re
from geopy.geocoders import GoogleV3
import json
from pymongo import MongoClient
from ConfigParser import SafeConfigParser
from bson.json_util import dumps

http = urllib3.PoolManager()
config = SafeConfigParser()
config.read('config.ini')
geolocator = GoogleV3(config.get('main', 'googleapi'))

client = MongoClient()
client = MongoClient("mongodb://localhost:27017")
db = client.res


shoplist = []

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

        province = details[3][:details[3].index("<br/>")]

        shoplist.append({"name": shop_name, "steetnr": details[1], "zipcodecomm": details[2], "province": province})

    index = 0
    for desc in soup.find_all("td", {"valign":"top", "class":"normal", "colspan":"5"}):
        obj = shoplist[index]
        resp = re.findall(r'\d+', desc.contents[0])
        if len(resp) > 0:
            obj["resp"] = re.findall(r'\d+', desc.contents[0])[0]
        else:
            obj["resp"] = ""
            
        obj["category"] = desc.b.text

        if db.shops.find({"name": obj["name"]}).count() == 0:

            location = geolocator.geocode(details[1] + ", " + details[2] + ", " + province)

            if location == None:
                lat = ""
                long = ""
            else:
                lat = location.latitude
                long = location.longitude

            obj["lat"] = lat
            obj["long"] = long

            result = db.shops.insert(obj)
            print(result)
        else:
            print("Shop already in database" + str(db.shops.find({"name": obj["name"]}).count()) + " " + obj["name"])

        index = index + 1


def main():
    print("main")

    steden = ["leuven"]
    radius = "100"

    for stad in steden:
         soup = BeautifulSoup(getpage("http://www.resplus.be/nl/index.asp?name=&keyword=&contact=&city=" + stad + "&radius=" + radius + "&ps_guide=&province=&pagelanguage=1&pid=..%2Fnbs%2Fclients")
                          , 'html.parser')
         getshops(soup)

    dumpJSON()


def dumpJSON():
    with open('data.json', 'w') as outfile:
        outfile.write("data = " + dumps(db.shops.find({"lat": {"$exists" : True, "$ne" : ""} })))

#TODO: write function to update empty lat and long values
if __name__ == '__main__':
    main()
