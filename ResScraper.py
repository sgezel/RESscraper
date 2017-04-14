import requests
import json
from pymongo import MongoClient
from ConfigParser import SafeConfigParser
from bson.json_util import dumps
from bs4 import BeautifulSoup


class ResScraper:
    config = SafeConfigParser()
    config.read('config.ini')
    client = MongoClient("mongodb://res:res@ds044979.mlab.com:44979/res")
    db = client.res

    def scrape(self):

        data = self.scrapeMerchants()
        # categories = self.scrapeCategories()

        shoplist = self.createShopList(data["data"])
        self.saveShopList(shoplist)
        self.cleanShops(shoplist)
        self.dumpJSON()

    def scrapeCategories(self):
        params = {
            'method': 'GET',
            'url': 'https://rds.res.be:88/rds/Categories/Sub?language=5&country=12&maincategory=-1'
        }

        return self.doRequest(params)

    def scrapeMerchants(self):
        params = {
            'method': 'GET',
            'url': 'https://rds.res.be:88/rds/Merchants/Find?language=5&country=12&filtertext=&filtertype=0&filterlatne=90&filterlonne=90&filterlatsw=-90&filterlonsw=-90&category=-1&subcategory=-1&page=1&pagesize=1000000002&randseed=944277&province=&city=&cityproximitymeters=100000000'
        }

        return self.doRequest(params)

    def scrapeDescription(self, merchantid):
        r = requests.get("http://res.be/nld/consumenten/merchant-detail/" + str(merchantid))

        soup = BeautifulSoup(r.text
                      , 'html.parser')

        return soup.find_all("div", {"class":"col-md-12 noPaddingPrint"})[0].p.string


    def doRequest(self, params):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'Host': 'res.be',
            'Referer': 'http://res.be/nld/consumenten/search-a-handelaar/s/v:50.89686150969607,3.435974054687449/z:8/s:/ts:0/c:-1/sc:-1'}

        r = requests.post("https://res.be/consumers/CallAPI", data=params, headers=headers)


        js = json.loads(r.text)

        return js

    def createShopList(self, shops):
        shoplist = []

        for shop in shops:
            cat_list = []
            for cat in shop["categories"]:
                cat_list.append(cat["name"])

            s = {
                "province": shop["province"],
                "category" : ", ".join(cat_list),
                "name": shop["name"],
                "zipcodecomm": shop["zip"] + " " + shop["city"],
                "resp": shop["respercent"],
                "long": shop["lon"].replace(",","."),
                "lat": shop["lat"].replace(",","."),
                "streetnr": shop["address"] + " " + shop["housenumber"],
                "id": shop["id"]
            }
            shoplist.append(s)

        return shoplist

    def saveShopList(self, shoplist):

        for shop in shoplist:
            if self.db.shops.find({"name": shop["name"], "streetnr": shop["streetnr"], "zipcodecomm": shop["zipcodecomm"]}).count() == 0:
                print("Adding shop " + shop["name"] + ", " + shop["streetnr"] + ", " + shop["zipcodecomm"])
                shop["description"] = self.scrapeDescription(str(shop["id"]))

                result = self.db.shops.insert(shop)
                print(result)

    def cleanShops(self, shoplist):

        print("Deleting removed shops: ")
        cursor = self.db.shops.find()

        for dbshop in cursor:
            found = False
            for shop in shoplist:
                if shop["name"] == dbshop["name"] and shop["streetnr"] == dbshop["streetnr"]:
                    found = True
                    break

            if not found:
                print "delete shop " + dbshop["name"]
                self.db.shop.delete(dbshop)

    def dumpJSON(self):

        with open( '/var/www/res/data.json', 'w') as outfile:
            outfile.write("data = " + dumps(self.db.shops.find({"lat": {"$exists": True, "$ne": ""}})))