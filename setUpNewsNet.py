#!/usr/bin/python3.5

from time import time
import requests
# from urllib.parse import urlparse
from tld import get_tld
import configparser
conf = configparser.ConfigParser()
conf.optionxform = str
conf.read('config.ini')
from pymongo import MongoClient


def set_up_tables():
    '''only sets up actors, as mongo lazily adds tables (collections)
    as needed (as i need indeces later that might be a mistake..)'''
    client = MongoClient(conf['database']['path'],
                         int(conf['database']['port']))
    db = client[conf['database']['mongo_db']]
    actors = db.newsNetActors

    # insert some actors
    url = conf['google-docs']['url']
    response = requests.get(url)
    assert response.status_code == 200, 'Wrong status code'
    # NB: the next line assumes there is a header row in the google doc
    for u in response.content.decode("utf-8").split("\n")[1:]:
        # the str.rsplit("/") could fuck up sites like nkr.no/ho/
        # with nrk.no/holmesund-i-brann
        # burde bare gjøres hivs vi har sites som er subdomener og ender
        # i tld (eg. stuff.site.se/)
        tmp_tld = get_tld(u.split("\t")[0], as_object=True)
        if tmp_tld.subdomain == '':
            domain = u.split("\t")[0]
        else:
            # remove trailing slash from sites with subdomains
            # eg. *.lokalavisen.dk/ or *.lokaltidningen.se/
            domain = u.split("\t")[0].rstrip("/")
#         print(u.split("\t"))

        doc = {
            "url": domain,
            "is_comp_site": u.split("\t")[1].strip(),
            "registered_domain": get_tld(u.split("\t")[0]),
            "lat": u.split("\t")[2],
            "lon": u.split("\t")[3],
            "local_domain": u.split("\t")[4].strip(),
            "name": u.split("\t")[5].strip(),
            "level": u.split("\t")[6].strip(),
            "country_tld": tmp_tld.suffix,
            "country": u.split("\t")[8].strip(),
            "owner": u.split("\t")[9].strip()
        }
        # print(doc)
        # import sys
        # sys.exit("stop!")
        # post_id = actors.insert_one(doc).inserted_id
        condit = {"url": domain}
        # print(condit)
        actors.update(condit, {"$setOnInsert": doc}, upsert=True)
        print("inserted data for:", doc['name'])


def main():
    t0 = time()
    print("Setting up tables in db from config.ini")
    set_up_tables()
    print("Done in ", format(time() - t0, '.3f'), "secs")
    print("Now you can run getNewsNet.py to start collect data")
    # drop with
    # db.newsNetActors.drop()


if __name__ == '__main__':
    main()
