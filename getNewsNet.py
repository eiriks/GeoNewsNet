#!/usr/bin/python3.5

from time import time
from datetime import datetime
import requests
import logging
import coloredlogs
from bs4 import BeautifulSoup
# import tldextract
from urllib.parse import urljoin  # , urlparse
from tld import get_tld
from pytrie import StringTrie
from multiprocessing import Pool  # processes
import configparser
conf = configparser.ConfigParser()
conf.optionxform = str  # stop confparser from lowercaseing stuff..
conf.read('config.ini')
# print(conf['database']['filename'])

from pymongo import MongoClient
# create a user-agent string with contact info
headers = {}
for key in conf['user-agent-string']:
    headers[key] = conf['user-agent-string'][key]

# List of exceptions from confic where lowercasing found urls is ok and right
lower_ok = [n.strip() for n in
            conf['allow_lowercase']['lowercase_ok'].split(",")]

# set up logging
logger = logging.getLogger("GeoNewsNet")
format = "%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)s] %(message)s"
# CRITICAL 50, ERROR 40, WARNING 30, INFO 20, DEBUG 10
# logging.basicConfig(level=logging.DEBUG, format=format)
coloredlogs.install(level=logging.DEBUG, fmt=format)  # , format=format
# hush requests...!
logging.getLogger("requests").setLevel(logging.WARNING)


class LinksExtractor:
    """Take a url from known news outlet.
    Look for links to other domains.
    Save the links out from this run.
    Save the freq dist for links out to each domain
    found.
    How deep should we go? one level? two?
    """

    def __init__(self, url, n_levels_deep=1,
                 is_composite=False):
        """..."""
        logger.info("init Class with '{}'".format(url))
        self.site = url
        self.full_domain = get_tld(url)  # top level domain
        self.links_out = []
        self.internal_links = []
        self.n_levels_deep = n_levels_deep
        self.is_composite = is_composite
        self.domains_we_study = StringTrie()  # prefix tree

        # set up mongodb
        self.client = MongoClient(conf['database']['path'],
                                  int(conf['database']['port']))
        self.db = self.client[conf['database']['mongo_db']]

        self.scraped = []  # init this with stuff from db
        add_previously_scraped = self.db.internal_links.find({
            "link_base_domain": self.full_domain
        }, {"link": 1})
        for doc in add_previously_scraped:
            self.scraped.append(doc['link'])

        # and a trie (prefex tree) https://pythonhosted.org/PyTrie/
        # to hold the domains we care about
        # http://stackoverflow.com/a/5435784/357387
        scope = self.db.newsNetActors.find({}, {"url": 1})
        for doc in scope:
            self.domains_we_study[doc['url']] = doc['url']

    def is_composite_actor(self, tld_url):
        if self.db.newsNetActors.find({
            "registered_domain": tld_url,
            "is_comp_site": {
                "$ne": "no"
            }
        }).count() == 0:  # 0 means not composite
            return False
        else:
            return True

    def has_class_but_no_id(self, tag):
        return tag.has_attr('class') and not tag.has_attr('id')

    def save_url_to_db(self, url, l, l_tld):
        # split intern & exstern
        if self.full_domain == l_tld:
            # internal - just append lo list
            if l not in self.internal_links:
                self.internal_links.append(l)
        else:
            # external links - save appropriately to db
            if l not in self.links_out:
                self.links_out.append(l)

            # figure out if target is composite
            if self.is_composite_actor(l_tld):
                try:
                    l_tld = self.domains_we_study.longest_prefix(l)
                except:
                    pass
            # print("l:", l, "l_tdl", l_tld)
            doc_external = {
                "from_url": url,
                "from_base_url": self.full_domain,
                "to_url": l,
                "to_base_url": l_tld,
                "found_date": datetime.now()
            }
            condit = {"from_url": url, "to_url": l}
            self.db.external.update(condit,
                                    {"$setOnInsert": doc_external},
                                    upsert=True)

    def save_composite_url_to_db(self, url, l, l_tld):
        '''If the url is from a composite newssite, we use a prefixtree
        to decide if a url is internal or external
        url = the url from where we found a link
        l = the url to where we found a link
        l_tld = base_url of found link (top level domain)
        '''
        # see if the target exists in the prefixtree
        try:
            p_base = self.domains_we_study.longest_prefix(l)
        except:
            p_base = None
        # if we found a longest prefix AND this the site we
        # examine right nows' url is in this base (actually equals.)
        if p_base and self.site == p_base:
            internal = True
        else:
            internal = False

        if internal:
            # store it for later iterations
            if l not in self.internal_links:
                self.internal_links.append(l)
        else:
            # external
            if l not in self.links_out:
                self.links_out.append(l)

            # figure out if target is composite
            # set l_tld to longest prefix if posible.
            if self.is_composite_actor(l_tld):
                try:
                    l_tld = self.domains_we_study.longest_prefix(l)
                except:
                    pass

            doc_external = {
                "from_url": url,
                "from_base_url": self.site,
                "to_url": l,
                "to_base_url": l_tld,
                "found_date": datetime.now()
            }
            condit = {"from_url": url, "to_url": l}
            self.db.external.update(condit,
                                    {"$setOnInsert": doc_external},
                                    upsert=True)

    def filter_links(self, link):
        '''http://stackoverflow.com/a/28905106/357387'''
        href = link and link.get('href')
        if href:
            return all([
                link,
                link.name == 'a',
                href,
                not link.has_attr('no_track'),
                not href.startswith(("mailto", "ftp", "tlf", "tel", "javasc",
                                     "sms", "//", "avisa@", "redaksjonen@",
                                     '#', "webcal")),
                '{' not in href,
                not href.endswith((".jpg", ".pdf", ".doc", ".xls", "jpeg",
                                   ".png", ".mov"))
            ])
        else:
            # logger.info("this link is no good: {}".format(link))
            return False

    def get_links(self, url):
        # store url as scraped
        self.scraped.append(url)
        # check if it is in db
        if not self.db.internal_links.find({'link': url}).count() > 0:
            # if not, insert new scraped url
            # get link_base_domain correct for composite sites...
            temp_tld = get_tld(url)
            # herpahps redundant, but do a check if this url is a composite
            # site in the actors collections
            if self.is_composite_actor(temp_tld):
                try:
                    temp_tld = self.domains_we_study.longest_prefix(url)
                except:
                    pass
            # print("url, temp_tld, l:237", url, temp_tld)
            # insert internal
            doc_internal = {
                "scraped": True,
                "link": url,
                "link_base_domain": temp_tld,
                "found": datetime.now()
            }
            self.db.internal_links.insert_one(doc_internal)
        # this try except should be rewritten,
        # there are more exceptions than you might thing.
        # only accept ok status, skipp all others.
        try:
            r = requests.get(url, headers=headers)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.TooManyRedirects,
                requests.exceptions.InvalidSchema,
                requests.exceptions.ChunkedEncodingError,
                requests.exceptions.ContentDecodingError,
                requests.exceptions.ReadTimeout):  # as e
            logger.debug("""Url dos not exist? (or too many redirects)
                         or invalid schema, or ChunkedEncodingError++
                         on {}""".format(url),
                         exc_info=True)
            return

        if r.status_code == requests.codes.ok:
            try:
                soup = BeautifulSoup(r.text, 'lxml')  # html.parser
            except:
                logger.debug("content not html? {}".format(url))
                return

            # logger.debug(soup)
            # use the filters - get links from where we are now.
            for link in soup.find_all(self.filter_links):
                l = link.get('href')
                # logger.debug(l)
                # fix internal to full length urls
                if not l.lower().startswith(("http://", "https://")):
                    l = urljoin(self.site, l)
                    # print("now its", l)
                # fix backwards errors from ystadsallehanda.se
                if l.lower().startswith("http://http://"):
                    l = l[7:]

                try:
                    l_tld = get_tld(l)
                except:
                    logger.info("at {} can't find tld for {}".format(url, l))
                    continue

                if len(l_tld) == 0:
                    l = urljoin(self.site, l)
                    l_tld = get_tld(l)
                    logger.debug("joined relative url {}".format(l))

                # NB: http://sn.dk/Naestved does not register any a-tags,
                # even if the soup object does contain 'em. (ugly fix added)
                if any(exc in l for exc in lower_ok):
                    l = l.lower()
                    l_tld = get_tld(l)
                    # logger.debug("exception! url .lower(): {}".format(l))

                if l in self.scraped:  # "already scraped"
                    continue

                if self.is_composite:
                    self.save_composite_url_to_db(url, l, l_tld)
                else:
                    # from_utl, to_url + tld
                    self.save_url_to_db(url, l, l_tld)
                # logger.debug(l)
        else:
            logger.debug("Status '{}' not ok: {}".format(r.status_code, url))


def scrape(url_tuple):
    exObj = LinksExtractor(url_tuple[0],
                           is_composite=url_tuple[1],
                           n_levels_deep=int(conf['search-depth']['depth']),  # noqa
                           )
    exObj.get_links(url_tuple[0])
    # simpler version of http://stackoverflow.com/q/12484113/357387
    # ensure we go n levels deep
    for i in range(exObj.n_levels_deep):
        potentials = list(set([n for n in exObj.internal_links
                               if n not in exObj.scraped]))
        # dont bother if we have no new potentials
        if len(potentials) > 0:
            logger.debug("* Round: {} with {} candidate urls"
                         .format(i+1, len(potentials)))
            # then loop though each of the new unknows
            for new_url in potentials:
                exObj.get_links(new_url)

    logger.debug("{} N out-lenks found - {}"
                 .format(url_tuple[0], len(exObj.links_out)))
    logger.debug("{} N scraped antall - {}"
                 .format(url_tuple[0], len(exObj.scraped)))
    logger.debug("{} N intrnal - {}"
                 .format(url_tuple[0], len(exObj.internal_links)))
    pot = len([n for n in exObj.internal_links if n not in exObj.scraped])
    logger.debug("{} N new links we can (could have) follow(ed): {}"
                 .format(url_tuple[0], pot))


def collect_data():
    to_scrape = []
    client = MongoClient(conf['database']['path'],
                         int(conf['database']['port']))
    db = client[conf['database']['mongo_db']]
    cursor = db.newsNetActors.find()  # .limit(5)
    for document in cursor:
        advanced = True if document['is_comp_site'].strip() != 'no' else False
        to_scrape.append((document['url'], advanced))
    # reverse order
    to_scrape = to_scrape[::-1]

    logger.debug("Got the sites to scrape {} stk, lets go..!"
                 .format(len(to_scrape)))

    # try to parallelize
    # http://chriskiehl.com/article/parallelism-in-one-line/
    # from multiprocessing.dummy import Pool as ThreadPool  # threads

    pool = Pool(24)  # ThreadPool(24)
    pool.map(scrape, to_scrape)
    pool.close()
    pool.join()
    logger.debug("function collect_data finnished peacefully")


def collect_data_fill_potential_holes(n=10):
    """148 sites had less than 100 internal, 100 had less than 10
    and are probably technical errors that needs to be fixed, hence
    this function. n=10 by default, but 100 seems more reasonable"""
    # connect
    client = MongoClient(conf['database']['path'],
                         int(conf['database']['port']))
    db = client[conf['database']['mongo_db']]
    cursor = db.newsNetActors.find()
    # build the list of all sites
    all_sites = []
    for document in cursor:
        advanced = True if document['is_comp_site'].strip() != 'no' else False
        all_sites.append((document['url'], advanced,
                         document['registered_domain']))
    # get the number of each site scraped urls (not inlcuding 0 scraped)
    cur = db.internal_links.aggregate([
        {"$group": {"_id": "$link_base_domain", "count": {"$sum": 1}}},
        {"$sort": {"count": 1}}
    ])
    all_in_db = {}  # if we have 0 in db, we need to know and add later
    for c in cur:
        all_in_db[c["_id"]] = c['count']

    rescrape_these = []
    for u in all_sites:
        test = u[2]
        if (u[1] is True):
            test = u[0]
        # find how many we have on this or 0 if not found
        if(all_in_db.get(test, 0) < n):
            # tuple (url.com, True)
            rescrape_these.append((u[0], u[1]))
    logger.debug("rescrape {} items".format(len(rescrape_these)))
    # then do the new scraping

    pool = Pool(24)  # ThreadPool(8)
    pool.map(scrape, rescrape_these)
    pool.close()
    pool.join()
    logger.debug("Done rescraping {} sites".format(len(rescrape_these)))


def delete_internal_with_low_n(n=10):
    '''Delete internal links where number of visited internal is lower
    than the input number. Used to re-run sites that looks like the scraping
    has not worked as intended...'''
    client = MongoClient(conf['database']['path'],
                         int(conf['database']['port']))
    db = client[conf['database']['mongo_db']]
    cur = db.internal_links.aggregate([
        {"$group": {"_id": "$link_base_domain", "count": {"$sum": 1}}},
        {"$sort": {"count": 1}}
    ])
    n_sites = 0
    n_links = 0
    for c in cur:
        n_sites += 1
        if(c["count"] < n):
            res = db.internal_links.remove({"link_base_domain": c["_id"]})
            logger.debug("removed {} internal @ {}".format(res['n'], c["_id"]))
            n_links += res['n']
    logger.debug("Removed {} links from a total of {}"
                 .format(n_links, n_sites))


def debug_these():
    # (url, is_composite_bool)
    suspects = [
        # ("http://sn.dk/naestved", True),
        # ('http://sverigesradio.se/kalmar/', True),
        # ('http://sverigesradio.se/malmo/', True),
        # ('http://www.stockholmdirekt.se/sodrasidan', True),
        # ('http://sn.dk/alleroed', True),
        # ('http://www.fyens.dk/langeland', True),
        # ('http://www.svt.se/nyheter/lokalt/stockholm', True),
        # ('http://www.svt.se/nyheter/regionalt/stockholm', True),
        # ('http://www.svt.se/nyheter/regionalt/smaland', True),
        # under here are sites with very few internal.
        # ('http://sn.dk/ugebladetvestsjaelland', ),  # broken internal logic
        ('http://nordjyske.dk/nyheder', True),  # fixed
        # ('http://sn.dk/nordvestsjaelland', ),  # not realy a portal
        ('erhvervsavisen.dk', False),  # scraping error?
        # ('http://www.helahalsingland.se/soderhamn', ),  # broken internal logic
        # ('http://www.nrk.no/ostafjells', ),  # rediects to http://www.nrk.no/telemark/
        ('nsnet.dk', False),  # scraping error?
        # ('http://www.nrk.no/nordnytt', ),  # 404 not a portal
        # ('http://www.dt.se/borlange', ),  # broken internal logic
        # ('http://www.dt.se/ludvika', ),  # broken internal logic
        # ('http://www.dt.se/hedemora', ),  # broken internal logic
        # ('http://www.helahalsingland.se/ljusdal', ),  # broken internal logic
        ('dknyt.dk', False),  # scraping error?
        # ('http://www.helahalsingland.se/bollnas', ),  # broken internal logic
        ('bmz.se', False),  # has frames like in 1996. skip this dinosaur
        # ('http://sn.dk/nordsjaelland', ),  # broken internal logic
        # ('http://www.dt.se/mora', ),  # broken internal logic
        # ('http://www.allehanda.se/harnosand', )  # broken internal logic
    ]
    # http://sn.dk/naestved lenker til http://sn.dk/Naestved som
    # dermed ikke regnes som intern (composite matcher url-streng)
    # min beste løsning: lag en liste i config-filen med sites der
    # det er ok å url.lower() for å finne matcher. Dette funker på sn.dk
    # (som) er skrudd svært merkelig sammen - men kan ikke garanteres å virke
    # på alle sites.

    # for s in suspects[6:7]:
    #     scrape(s)

    # find sites with too few links to be correct:
    pass


def main():
    t0 = time()
    # helper function to fix holes in the data
    # debug_these()
    delete_internal_with_low_n(10)
    collect_data_fill_potential_holes(80)
    # the core program
    # collect_data()
    print("Done in ", format(time() - t0, '.3f'), "secs")
    logger.debug("Finnished in  {} secs".format(format(time() - t0, '.3f')))

if __name__ == '__main__':
    main()
    #
    # def mongo_stuff():
    #     #
    # db.internal_links.aggregate([
    #     {"$group" : {_id:"$link_base_domain", count:{$sum:1}}},
    #     {"$sort": { count : 1 } }
    # ])
    #     #
    #     # db.getCollection('internal_links').find({}).count()
    #     # 3623425
