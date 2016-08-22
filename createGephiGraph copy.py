#!/usr/bin/python3.4
# coding: utf-8
__author__ = 'eirikstavelin'
__version__ = '0.0.1a'

import sys
import os
import networkx as nx
from time import time
from collections import Counter
import configparser
conf = configparser.ConfigParser()
conf.optionxform = str
conf.read('config.ini')
from pymongo import MongoClient

# db
client = MongoClient(conf['database']['path'], int(conf['database']['port']))
db = client[conf['database']['mongo_db']]


def load_lat_lons():
    docs = db.newsNetActors.find({}, {
        "url": 1,
        "is_comp_site": 1,
        "registered_domain": 1,
        "lat": 1,
        "lon": 1
    })
    # sql = """SELECT  url, is_comp_site, registered_domain, lat, lon
    #          FROM newsNetActors"""
    # cur.execute(sql)
    # rows = cur.fetchall()
    d = {}
    for row in docs:
        if row["is_comp_site"] != 'no':
            # advanced case
            d[row["url"]] = (float(row["lat"]), float(row["lon"]))
        else:
            # normal case
            d[row["registered_domain"]] = (float(row["lat"]), float(row["lon"]))  # noqa
    # print("Loaded lat/lons")
    return d


def get_lat_lon_from_dict(url, d):
    if url in d:
        return d[url]
    else:
        return (0.0, 0.0)


def get_visits(base_domain):
    """ return the number of uniqe internal links we have visited to collect
    external links for a give base_domain (bt.no for simple and
    http://nrk.no/hordaland) for composite """

    # this is select distinct count - lots harder with mongo..
    n = db.internal_links.aggregate(
        [
            {"$match": {"link_base_domain": base_domain}},
            {"$group": {"_id": "$link"}}
        ]
    )
    n = len(list(n))
    return int(n)


def db2gexf3(filname):
    d = load_lat_lons()
    # sql = '''SELECT url, is_comp_site , registered_domain, country FROM
    #            newsNetActors
    #          '''  # WHERE url LIKE "%nrk%"
    # cur.execute(sql)
    # rows = cur.fetchall()
    rows = db.newsNetActors.find({}, {
        "url": 1,
        "is_comp_site": 1,
        "registered_domain": 1,
        "country": 1,
        "country_tld": 1,
        "level": 1,
        "name": 1
    })
    G = nx.DiGraph()  # Graph or DiGraph()
    scope_of_study = []  # just to keep track of number of newsoutlets
    # first lets add all newssites
    for r in rows:
        # I also want to know how many urls we crawled
        # in order to get the number of out lainks (added later)
        if r["is_comp_site"].strip() != "no":
            # a composite site - use url
            n = get_visits(r["url"])
            G.add_node(r["url"],
                       latitude=get_lat_lon_from_dict(r["url"], d)[0],   # lat
                       longitude=get_lat_lon_from_dict(r["url"], d)[1],  # lng
                       country=r["country"],
                       tld=r['country_tld'],
                       n_uniqe_internal=n,
                       level=r['level'],
                       name=r['name']
                       )
            scope_of_study.append((r["url"], True))  # is special
        else:
            # a "normal site" - use registered domain
            n = get_visits(r["registered_domain"])
            G.add_node(r["registered_domain"],
                       latitude=get_lat_lon_from_dict(r["registered_domain"], d)[0],   # lat
                       longitude=get_lat_lon_from_dict(r["registered_domain"], d)[1],  # lng
                       country=r["country"],
                       tld=r['country_tld'],
                       n_uniqe_internal=n,
                       level=r['level'],
                       name=r['name']
                       )
            scope_of_study.append((r["registered_domain"], False))  # !special
    print(G)

    print(G.edges(), "\t n edges: ", G.number_of_edges())
    print(G.nodes(), "\t\t n nodes: ", G.number_of_nodes())
    print("n scope_of_study", len(scope_of_study),
          "(set)", len(set(scope_of_study)))
    print("*"*50)
    print()

    # then add relations
    # as this is only done to create gephi graph
    # and the special and normal cases are now mixed
    # we can afford to to this the "expencive way"
    # and query in a loop..
    scope_list = [nn[0] for nn in scope_of_study]

    for t in scope_of_study:
        print("this entity: ", t)  # ('http://www.nrk.no/buskerud/', True)
        # create a counter from this utl (t[0])
        cnt = Counter()

        # this query is slow. Why?
        # sql = """SELECT * FROM external_links WHERE from_base_url = ? """
        # cur.execute(sql, (t[0],))
        # rows = cur.fetchall()
        rows = db.external.find({
            "from_base_url": t[0]
        })
        for ro in rows:
            if ro["to_base_url"] in scope_list:
                cnt[ro["to_base_url"]] += 1
        print()

        # now convert counter to weight in egde
        for k, v in cnt.most_common():
            print(t[0], "-->", k, "n=", v)
            # compute distance in km and add as attr to edge
            # print(v, G.node[t[0]]['n_uniqe_internal'], str(t[0]+" - "+k))
            v_over_internal = 0
            if not v == 0 and not G.node[t[0]]['n_uniqe_internal'] == 0:
                v_over_internal = v/float(G.node[t[0]]['n_uniqe_internal'])
            G.add_edge(t[0], k, weight=v, w_over_internal=v_over_internal,
                       Label=str(t[0]+" - "+k))
    # create folder for grphi files, if not exists
    print()
    folder = "./graph_files/"
    if not os.path.exists(folder):
        os.makedirs(folder)
    nx.write_gexf(G, folder+filname)
    print("Wrote gephi file: ", filname)

if __name__ == '__main__':
    try:
        filename = sys.argv[1]
    except:
        print("createGephiGraph.py filename.gexf")
        sys.exit(0)
    if len(filename) > 6 and filename.endswith(".gexf"):
        start = time()
        db2gexf3(filename)
        print("Done in %s" % (time()-start))
    else:
        print("createGephiGraph.py filename.gexf")
