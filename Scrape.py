from bs4 import BeautifulSoup
import urllib3
import re
from geopy.geocoders import GoogleV3
from pymongo import MongoClient
from ConfigParser import SafeConfigParser
from bson.json_util import dumps
import json
import operator

http = urllib3.PoolManager()
config = SafeConfigParser()
config.read('/root/RESscraper/config.ini')
geolocator = GoogleV3(config.get('main', 'googleapi'))

client = MongoClient()
client = MongoClient("mongodb://"+ config.get('db', 'username') + ":" + config.get('db', 'password') + "@" + config.get('db', 'host') + ":" + config.get('db', 'port')+"/" + config.get('db', 'db'))
db = client.res


shoplist = []

def getpage(url):
    try:
        request = http.request("GET", url)
        encoding = request.encoding if 'charset' in request.headers.get('content-type', '').lower() else None
        return {"data": request.data, "encoding": encoding}
    except urllib3.exceptions.HTTPError:
        print("error")
    return {}

def getshops(soup):

    shoplist = []
    for shop in soup.find_all("td", {"valign":"top", "width":"30%"}):
        details = [x.strip() for x in str(shop.a.contents).split('<br>')]
        shop_name = details[0]
        shop_name = shop_name[details[0].index("\\r\\n\\r\\n\\t\\t\\t\\t\\t\\t\\t") + len("\\r\\n\\r\\n\\t\\t\\t\\t\\t\\t\\t"):-2].encode('utf-8').strip()

        province = details[3][:details[3].index("<br/>")]

        shoplist.append({"name": shop_name.encode('utf-8').strip(), "streetnr": details[1].encode('utf-8').strip(), "zipcodecomm": details[2].encode('utf-8').strip(), "province": province.encode('utf-8').strip()})

    index = 0
    for desc in soup.find_all("td", {"valign":"top", "class":"normal", "colspan":"5"}):
        obj = shoplist[index]
        resp = re.findall(r'\d+', desc.contents[0])
        if len(resp) > 0:
            obj["resp"] = re.findall(r'\d+', desc.contents[0])[0].encode('utf-8').strip()
        else:
            obj["resp"] = ""

        if desc.b != None:
            obj["category"]=[]
            cat_list = desc.b.text.encode('utf-8').strip().split("|")
            for cat in cat_list:
                obj["category"].append(cat.strip())
        else:
            obj["category"] = ""

        obj["description"] = desc.contents[2][3:]

        if db.shops.find({"name": obj["name"], "streetnr": obj["streetnr"], "zipcodecomm": obj["zipcodecomm"]}).count() == 0:

            print("new shop: " + obj["name"] + "    address: " + obj["streetnr"] + ", " + obj["zipcodecomm"])
            location = geolocator.geocode(obj['streetnr'] + ", " + obj["zipcodecomm"])

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
        # else:
        #     print("Shop already in database " + obj["name"])

        index = index + 1


def main():
    getShops()


    # updateLatLong()

    # cleanup()
    # listcat()
    # updateDesc()

    dumpJSON()

def getSoup(url):
    page = getpage(url)
    soup = BeautifulSoup(page["data"]
                          , 'html.parser',from_encoding=page["encoding"])

    return soup

def getShops():
    steden = ["leuven", "brugge", "hasselt", "antwerpen", "namen", "gent", "charleroi", "Huy"]
    landen = [".OTHER+COUNTRIES", ".NEDERLAND", ".GD+LUXEMBOURG", ".FRANCE", ".ESPANA+-+VALENCIA", ".ESPANA+-+CATALUNYA", ".ESPANA+-+CANAIRES", ".ESPANA+-+ANDALUSIA"]
    radius = "75"

    for stad in steden:
        print("getting shop around " + stad +  " (" + radius + "km)")
        url = "http://www.resplus.be/nl/index.asp?name=&keyword=&contact=&city=" + stad + "&radius=" + radius + "&ps_guide=&province=&pagelanguage=1&pid=..%2Fnbs%2Fclients"
        getshops(getSoup(url))

    for land in landen:
        url = "http://www.resplus.be/nl/index.asp?name=&keyword=&contact=&city=&radius=" + radius + "&ps_guide=&province=" + land + "&pagelanguage=1&pid=..%2Fnbs%2Fclients"
        print("getting shops in " + land)
        getshops(getSoup(url))

def dumpJSON():
    with open(config.get('output', 'location') + 'data.json', 'w') as outfile:
        outfile.write("data = " + dumps(db.shops.find({"lat": {"$exists" : True, "$ne" : ""} })))

def updateLatLong():
    cursor = db.shops.find({"lat":""})
    for shop in cursor:
        print("updating  " + shop["name"])
        location = geolocator.geocode(shop["streetnr"].encode('utf-8').strip() + ", " + shop["zipcodecomm"].encode('utf-8').strip())

        if location != None:
            print("old: " + str(shop["lat"]) + ", " + str(shop["long"]))
            print("new: " + str(location.latitude) + ", " + str(location.longitude))
            if location != None:
                if location.longitude != shop["long"] and location.latitude != shop["lat"]:
                    db.shops.update_one({'_id':shop["_id"]}, {'$set':{"lat": location.latitude, "long":location.longitude}}, upsert=False)

def cleanup():
    cursor = db.shops.find()
    for shop in cursor:
        cleaned_cat = []
        for cat in shop["category"]:
            cleaned_cat.append(cat.strip())

        #print(cleaned_cat)
        db.shops.update_one({'_id':shop["_id"]}, {'$set':{"category": cleaned_cat, "streetnr": shop["streetnr"].encode("utf8","ignore"),"zipcodecomm": shop["zipcodecomm"].encode("utf8","ignore"),"province": shop["province"].encode("utf8","ignore")}}, upsert=False)

def updateDesc():
    steden = ["leuven"]
    landen = [".OTHER+COUNTRIES", ".NEDERLAND", ".GD+LUXEMBOURG", ".FRANCE", ".ESPANA+-+VALENCIA", ".ESPANA+-+CATALUNYA", ".ESPANA+-+CANAIRES", ".ESPANA+-+ANDALUSIA"]
    radius = "100"

    for land in landen:
        soup = BeautifulSoup(getpage("http://www.resplus.be/nl/index.asp?name=&keyword=&contact=&city=&radius=" + radius + "&ps_guide=&province=" + land + "&pagelanguage=1&pid=..%2Fnbs%2Fclients")
                          , 'html.parser')

    # for stad in steden:
    #     soup = BeautifulSoup(getpage(
    #         "http://www.resplus.be/nl/index.asp?name=&keyword=&contact=&city=" + stad + "&radius=" + radius + "&ps_guide=&province=&pagelanguage=1&pid=..%2Fnbs%2Fclients")
    #                          , 'html.parser')
        shoplist = []
        for shop in soup.find_all("td", {"valign": "top", "width": "30%"}):
            details = [x.strip() for x in str(shop.a.contents).split('<br>')]
            shop_name = details[0]
            shop_name = shop_name[details[0].index("\\r\\n\\r\\n\\t\\t\\t\\t\\t\\t\\t") + len("\\r\\n\\r\\n\\t\\t\\t\\t\\t\\t\\t"):-2]

            province = details[3][:details[3].index("<br/>")]
            shoplist.append({"name": shop_name, "streetnr": details[1], "zipcodecomm": details[2], "province": province})

        index = 0
        for desc in soup.find_all("td", {"valign": "top", "class": "normal", "colspan": "5"}):
            obj = shoplist[index]

            print(shoplist[index])

            resp = re.findall(r'\d+', desc.contents[0])
            if len(resp) > 0:
                obj["resp"] = re.findall(r'\d+', desc.contents[0])[0]
            else:
                obj["resp"] = ""

            obj["category"] = desc.b.text.split("|")
            print(desc.contents[2])

            cursor = db.shops.find({"name": obj["name"], "streetnr": obj["streetnr"], "zipcodecomm": obj["zipcodecomm"]})
            for shop in cursor:
                db.shops.update_one({'_id': shop["_id"]}, {'$set': {"description": desc.contents[2][3:], "category":desc.b.text.split("|")}})
                # print(desc.contents[2][3:])
            index = index + 1

def listcat():
    cursor = db.shops.find()
    catlist = {}
    for shop in cursor:
        for cat in shop["category"]:
            if cat not in catlist:
                catlist[cat] = 1
            else:
                catlist[cat] = catlist[cat] + 1

    print(catlist)
    with open('cat.json', 'w') as outfile:
        json.dump(sorted(catlist.items(), key=operator.itemgetter(1)), outfile)

if __name__ == '__main__':
    main()
