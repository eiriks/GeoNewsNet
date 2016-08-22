# GeoNewsNet - the Karlstad-Bergen model of how online news sites link each other
A program for analysis of how websites link to each other. The background of the software is a research collaboration between researchers from Karlstad and Bergen, to investigate how the scandinavian online news organizations link across geography, ownership, local/region/national scope, funding models, etc.


Set up the sqlite tables with (make sure the config.ini is ok and you google doc ready):
> python setUpNewsNet.py

The collect data
> python getNewsNet.py

And finally generate a graph file for analysis
> python createGephiGraph.py filename.gexf

## Dependencies
pip install <module>

- requests
- tld
- beautifulsoup4
- pytrie
- networkx


## Config file
Change the config file to work with your domain of study.


## mongo version
start mongodb with
    mongod

* må adde indexer for mongo
     db.newsnet
     db.external.createIndex( { "to_url": 1, "from_url": 1 }, {background: true} )
     Btree::insert: key too large to index, failing newsnet.external.$to_url_1_from_url_1 1100 { : "http://www.facebook.com/sharer.php?p%5Bsummary%5D=Charlie%2520Yvander%2520och%2520Niklas%2520Eriksson%2520driver%2520sedan%2520ett%2520%25C3%25A5r%252...", : "http://www.dt.se/dalarna/alvdalen/synskadade-fick-kora-snoskoter" }
     db.external.ensureIndex( { "to_url": 1, "from_url": 1 }, {background: true} )
     # also fails
     db.external.createIndex( { "from_url": "hashed" }, {background: true} )
virker!
Men speeder et av to felter opp spørringen min? Kanskje ikke.. Kan ikke bruke
hased index i compund index. Sier manualen..

Lage index for createGephiGraph:
    db.external.createIndex( { "from_base_url": "hashed" }, {background: true} )


## General algorithm
We populate a database table with as list of urls with corresponding coordinates for this urls (a newsroom) location.

url	is_composite_site	lat	lon	Local_domain	News_Outlet_Name	Level
http://birkenes-avisa.no/	no	58.334682	8.231821	Birkeland	Birkenes-Avisa	Local	Aust-Agder
http://bjuv.lokaltidningen.se/		56.243771	12.862725		Lokaltidningen Söderåsen	lokal/regional	Ängelholm

1. We visit each of these urls. We collect internal links and keep track of these in a list.
External links are stored to db.

2. The internal links we have found, and not yet visited, we visit and store external links to the database and keep track of new internal links in our list.

3. Repeat step 2 for as many "levels deep" we feel the need to map out. This task will grow to a really big task quite fast.


Note: To go 2 levels deep (after the initial list is generated from visiting the "clean" starting url) will get you far, going 4 leves deep makes this a very slow process if we examine a "old", big and complex site. Remember that most web content tend to continue to exist online, even if its not easy to find from the front page on the site. If you run into sites with slow response time (e.g. not cashed hard) this also can become a long wainting game..

### Creating graphs
Run the createGephiGraph.py file to genereate .gexf-files that can be opened and studied in Gephi [https://gephi.org/].
Remember to do this after you have collected data with getNewsNet.py


### Log
crashed on vk.se
requests.exceptions.InvalidSchema: No connection adapters were found for '.http://www.vk.se/706572/kommunen-slutar-med-krankande-test'
--> added exception for InvalidSchema
With 4 levels deep, we stick on some sites (e.g. vg for almost interneties).

My v2 (2 levels deep) also died when my internet connection broke during the storm.

Når vi skraper sammensatte, som http://www.dt.se/ludvika
ser det ut som vi ikke finner stort. Dette kan være fordi dt.se allerede er
scrapet, men kan det også hende at interne/scraptede/etc settes feil på
sammensatte url-er når objektet instansieres?


restart på p4.no (status i top indikerer at den har sovna, ting stod stille. dette var 2levels dyp, tror jeg)

restart (den grådigre 4 leves neep), ganse nært siste site, tror jeg.


- sn.dk har et meget pussig oppsett. sn.dk funker mens http://sn.dk/Naestved/ funker ikke.
- http://sn.dk/naestved/ funker. mens det finnes mange lenker av typen
http://sn.dk/Naestved/Dagli-Brugsen-faar-en-ekstra-chance/artikel/556209
Pussig!

Vurderer å skippe sn.dk... Eller skulle jeg tvinge alle entiteter ned i lower-case?


- Subdomener fra nwt.se
Fungerer slik som at de oppfattes som eksterne domener.
Hentes ikke med som innen vårt "scope of study" når vi lager grafer.
I forhold til nwt.se/amal (eller liknende) sånes jeg dette er ok.
- domener med subdomener ([a-z].lokalavisen.dk/ or [a-z].lokaltidningen.se/) stripper jeg vekk trailing slash .rstrip("/") som en sær-behandling
da disse har en tendesn til å lenke hverandre uten trailing slahs
(i den svenske familien i alle fall). Dette har ulempen at andre domener
med www som dubdomener (http://www.barometern.se/oskarshamn/) også mister
trailing slahs. Bare et problem hvis i tilfeller ala http://www.barometern.se/oskarshamn-i-brann der entiteten
http://www.barometern.se/oskarshamn forsvinner i resten av lenken.
Jeg anser det som ok.


# Runde 2 av innsamling - etter bugs er borte (håper jeg..)
bruker mosh for å ha mobilt shell.

screen - the basics
    screen
    ctrl + a :sessionname geonews
    # eller
    screen -S geonews -L # (-L for log)
    ctrl + a d (setter session i detached mode)
    screen -ls (lister ut dtached screens)
    screen -r <navn> (kobler på)

Kjør:
$ screen -S geonews -L
(nyhetskategorier) est040@nelson:~/GeoNewsNet$ deactivate
est040@nelson:~/GeoNewsNet$ source geonews/bin/activate

# NB: ikke ctrl + d nå.. (ikke kill prosessen, bruk ctrl + a d)
# kjør scriptene
(geonews) est040@nelson:~/GeoNewsNet$ python3 setUpNewsNet.py
(geonews) est040@nelson:~/GeoNewsNet$ python3 getNewsNet.py

ctrl + a d (detach fra screen)

vent "noen dager"

connect med screen -r geonews

når du er deconnected can du sjekke "status" med:
    tail screenlog.0

screen -r geonews
14/3. db'n har ikke addda noe nytt siden 12/3. Jeg stopper og starter på nytt.. Hadde kommet til dagen.no

ctrl + a d (for å koble ut igjen.)

Angrer som en hund på at jeg gikk for sqlite. Tror det er indexene mine som gjør at dette går så seint. Burde gått for mysql eller mongodb i stede..
.. og det burde vært paralellisert...




# Speed issues.
The code does what it is intended to now, but it is slow. I think I might have put the indices on the wrong fields...

### crazy slow (5.5 hours..)
Wrote gephi file:  halfbaked.gexf
Done in 20262.76573419571

    sqlite> SELECT * FROM external_links WHERE from_base_url = "http://sn.dk/naestved";
    Run Time: real 80.402 user 3.325506 sys 15.995853

    sqlite> .indices external_links
    external_from_index
    external_to_index

lager index på from_base_url
    sqlite> CREATE INDEX external_from_url_base_index ON external_links (from_base_url);
    Run Time: real 69.543 user 12.016445 sys 13.564150

    sqlite> SELECT * FROM external_links WHERE from_base_url = "http://sn.dk/naestved";
    Run Time: real 0.000 user 0.000093 sys 0.000044

### Not so crazy slow (>3min)
Wrote gephi file:  halfbaked2.gexf
Done in 155.7858419418335


sqlite> SELECT COUNT(link) as n, * FROM  internal_links WHERE link_base_domain = "http://hoganas.lokaltidningen.se" GROUP BY link;

##with n internal lookup
Wrote gephi file:  halfbaked2.gexf
Done in 880.4132630825043


## sverigesradio
sverigesradio is not a composite site like the others. It has sections form various districts (sverigesradio.se/place) but internally it works by linkin these as integers, http://sverigesradio.se/sida/artikel.aspx?programid=94&artikel=6422029 where 94 is Gotland, etc. I will not consider sverigesradio as a composite site.

## 1 mai søndag - fixing the last bits
- switched to lxml as parser
- added country for all sites.
- SVTs urls are wrong. they say nyheter/regional/{place} but should say nyheter/lokal/{place}
- now total of sites is 673 (sverigesradio is reduced to one actor)
- droped newsNetActors collecttion, and reloaded from google docs

### ownership
Norway - http://www.medietilsynet.no/mediebildet/eierskap/




And also:
RQ: does ownership matter for linking? Do newspapers within the same corporation link more to each other than to others?
RQ: what type of content is linked the most? (e.g. sports/poltiics etc - if it is possible to content analyse the urls down the line…)
RQ: what characterises the smaller papers that don’t link out at all? (there seems to be quite a few of these) e.g. where are they located? Coast? North? Independent ownership? etc
RQ: What is the average geographical distance (in km) between major/minor linking nodes? (if this is possible to find out)
RQ: what characterises the ‘islands’ of networks (e.g. nrk has its own internet)

Is a good way to go about this just to find the answers to these questions first? And then group the RQs under the abstracts and write out the analysis?

One more thing: I have recruited Aske Kammer to the project. He’s the only Dane (according to himself, and I believe him) that knows anything about newspaper structures and media regulation in Denmark. I’ve sent him our abstracts and shown him the programme. I’ll link him to our docs so he can check our data. He’s aware he’ll be fourth author on this, but happy to join our project. Hope that’s good with you two.



## Question I want to answer

### From the "Networked Intermedia Agenda Setting" google doc

a) How interlinked is the Scandinavian news ecology overall? (we can say something about this, but have nothing to compare to)
    Avg degree, some measure of density,
b) How interlinked are the countries overall? (this we can answer because we can compare them)
    avg degree pr country. distance across theach sub-network. how close to "complete" the networks are.
c) Systematic interlinking? What is more significant (might have to do a statistical analysis of this?)
    x) ownership,
    y) geographic location, or
    z) size (local/regional/national)? (this we can answer, if we rank all the nodes according to centrality or connectedness, then run against ownership and size (circulation), and size - or according to distance from the capital, in km normalised/average, might be tricky for Denmark)
d) Super-hubs and superhighways: for each country and what are their similarities and differences (this we can answer). Are there Scandinavian superhubs and superhighways? (can we answer) (importance of national/linguistic borders) Does Scandinavia link beyond itself? (might be able to answer based on URL rankings)
    hubs (from HITS), autority, pagerank + betweeness centrality + degree.
e) Intermedia agenda setting: characteristics of the Scandinavian hyperlink ecology: to what extent are agendas local, national and nordic? To what extent are they international? (might be able to do this based on URL rankings) (tighter links the lower/more local you get or tighter links the more nation you get? The network is tighter the higher you get in the ecology)


2. Network brokers:
Network Centrals: who constitute the ‘hubs’ in the network(s)? (who feeds whom?) (are regional papers brokers between local and national agendas?) (we can answer this) (bilateral relations, must identify regional brokers then, 5-6 players in Norway)
Is centrality/broker position more related to x) ownership, y) geographic location, or z) size (local/regional/national)? (statistical analysis)
Network direction: Which way does information flow? Upward (from local to regional, from regional to national), downward (from national to regional, from regional to local) or sideways (within corporations and local to local, regional to regional or national to national within regions)? (this we might be able to answer)
Media type (the role of broadcasters) - are PSBs more important than newspapers in brokering the information flow? (characteristics of Scandinavian media system)(PSBs have their ‘own’ internet based on CMS-scaling/architecture, biased towards own ecology; systematic linking - we can create threshold to determine that these are ‘automated’)
Intermedia agenda setting: the importance of brokers in linking national online news agendas + the importance of corporate ownership for ‘connectivity’ + the importance of place (geographical centrality) for intermedia agenda setting ‘power’? (this we can answer)

3. Network shadows (excluded/disconnected):
Network exclusion: what portion of the network is excluded from the agenda setting ‘flow’? (threshold must be determined, percentage or random number or ‘scaled’ number) What characterises exclusion: ownership, geographic location or size? (per country)  (decide on cut-off point for inclusion/exclusion)
Centre/periphery dimensions: The importance of North/south dimensions + proximity to the capital for network centrality in the three countries. (statistical analysis)
Intermedia agenda setting: Implications of participation in hyperlinked ecology for ability to perform intermedia agenda setting (slightly tautologic sentence, but should be entry point to discuss who are excluded - most likely these will be local newspapers)
So what?



- who are the hubs in Scandinavia?
    Def: Hubs are nodes with high degree and betweeness centrality.
    Degree = inn links + out links.
    For all countries: (avg degree 19.9)
	top10:
    dagbladet.no	307
    vg.no	288
    tv2.no	263
    aftenposten.no	254
    aftonbladet.se	250
    http://www.expressen.se	225
    politiken.dk	217
    ekstrabladet.dk	212
    adressa.no	208
    svd.se	186

    All countries are represented in the top10 list.
    I read this like the countries are relatively comparable and that the data collection method has not favoured any of the countries.

    Norway: (avg 20.1)
    # filter on equal -> country -> "norway"
    # rerun statistics -> average degree
    dagbladet.no	227
    vg.no	217
    tv2.no	210
    aftenposten.no	190
    adressa.no	162
    nettavisen.no	157
    dn.no	142
    vl.no	137
    ba.no	133
    nordlys.no	130

    # Sweden: (avg 14.7) <- considerably lower that no & dk. Sweden is less densely connected than no & dk.
    aftonbladet.se	171
    http://www.expressen.se	150
    svd.se	130
    dn.se	122
    sverigesradio.se	111
    sydsvenskan.se	88
    gp.se	86
    http://www.dt.se	82
    vk.se	79
    metro.se	78

    # Denmark (avg 19.0)
    politiken.dk	136
    ekstrabladet.dk	130
    bt.dk	119
    ing.dk	119
    jyllands-posten.dk	118
    http://lokalavisen.dk	106
    information.dk	97
    http://hilleroed.lokalavisen.dk	96
    http://odense.lokalavisen.dk	92
    http://sn.dk	91

    # betweeness centrality
    # high betweeness centrality indicate brokers. not neccesarily those with the most links, buth thos who bridge many other nodes and connect sub-networks.
    " A node with high betweenness has great influence over what flows -- and does not -- in the network. "

    # All counties:
    Diameter: 8
    Radius: 0
    Average Path length: 2.9867914111522045
    Number of shortest paths: 336902

    ekstrabladet.dk	41263.93636843192
    dagbladet.no	29611.224392797114
    aftonbladet.se	27663.82829942289
    http://www.expressen.se	26885.243524572707
    bt.dk	25917.69692662152
    politiken.dk	25621.63665811628
    http://sn.dk	24143.091811246548
    vg.no	23409.96047976205
    tv2.no	20882.578110514445
    aftenposten.no	17786.310645656176

    # Norway
    Diameter: 5
    Radius: 0
    Average Path length: 2.209987950880611
    Number of shortest paths: 39007

    dagbladet.no	4454.433816613989
    tv2.no	3527.9099772020304
    vg.no	3486.637313937973
    adressa.no	2861.665249068022
    aftenposten.no	2510.561352960613
    aftenbladet.no	1639.330697848793
    vl.no	1231.4625231848288
    nettavisen.no	1183.553803202622
    bt.no	1175.575012093173
    http://www.nrk.no/sognogfjordane	1175.2475101928578


    # Sweden
    Diameter: 6
    Radius: 0
    Average Path length: 2.5861001782890973
    Number of shortest paths: 29727

    aftonbladet.se	5803.547137243973
    http://www.expressen.se	5609.396352495715
    dn.se	2472.5492983872805
    http://nwt.se	2105.714641924687
    http://landskrona.lokaltidningen.se	2040.7825600906715
    http://www.stockholmdirekt.se	2011.9543219923016
    sydsvenskan.se	1982.2296656207
    svd.se	1953.916633234799
    http://lund.lokaltidningen.se	1452.8707196354098
    http://www.expressen.se/kvallsposten	1234.5744801655057


    # Denmark
    Diameter: 7
    Radius: 0
    Average Path length: 2.7496524533375877
    Number of shortest paths: 43879

    ekstrabladet.dk	9172.043195072005
    http://sn.dk	7476.216659506314
    bt.dk	6184.624521304597
    ing.dk	4924.781942814383
    politiken.dk	4553.08232835623
    tv2.dk	4502.381811943395
    http://sn.dk/vordingborg	3968.782662034418
    http://www.dr.dk/nyheder	3253.3922526212164
    jyllands-posten.dk	2646.7783662689953
    http://www.fyens.dk	2068.7279521779947

    HUBS are also a measure from the HITS algorithm, identifying ca 5 big hubs in each country. The authority measure from the same method identifies more or less the same nodes.
    PageRank is a bit stricter, giving us 3-4 big nodes in each countries:
    no -> vg, dagbladet, tv2, aftenposten
    se -> expressen, dn, aftonbladet
    dk -> ekstrabladet, politiken, bt




- An oposite: who are not central, not brokers. who are "off the race"?

Sites order by dregree asc, with max(order) 2. Notice the nr of internal scraped to get these, this is not because of lack of data, this is just the fact that these site rarely link other newssites in our sample. It can be skewed because of pay walls, but that does not change the fact that these are isolated in regard to a casual reader (without a subscription).

Site	Degree	Betweeness central	n_internal_scraped	level
bha.dk	0	0.0	3090	local
oehf.dk	0	0.0	1729	local
oyblikk.no	0	0.0	142	local
folkebladet.dk	0	0.0	1217	local
graastenavis.dk	0	0.0	92	local
alingsaskuriren.se	0	0.0	42	local
http://www.vamdrup.dk/news	0	0.0	481	local
uge-avisen.net	0	0.0	774	local
lyngposten.dk	0	0.0	280	local
sydvesten.no	0	0.0	249	local
vestnesavisa.no	0	0.0	60	local
galtenfolkeblad.dk	0	0.0	2017	local
midtvendsysselavis.dk	0	0.0	44	local
blekingeposten.se	0	0.0	24	local
gudenaadalens-avis.dk	0	0.0	383	local
klt.nu	0	0.0	57	regional
vestavind-sveio.no	0	0.0	49	local
vaksdalposten.no	0	0.0	163	local
meloyavisa.no	0	0.0	230	local
sallingavis.dk	0	0.0	117	local
hf.no	0	0.0	477	local
ugeavisenkarup.dk	0	0.0	1241	local
folkebladet.info	0	0.0	2244	local
farsoavis.dk	0	0.0	2326	local
http://minby.dk/vanloese-bladet/	0	0.0	431	local
gladsaxebladet.dk	0	0.0	1848	local
dragoer-nyt.dk	0	0.0	764	local
vesthimmerlandsavis.dk	0	0.0	1033	local
kungalvsposten.se	0	0.0	361	local
fjendsfolkeblad.dk	0	0.0	1598	local
sydtid.dk	0	0.0	8421	local
rnn.dk	1	0.0	2083	local
lanstidningen.se	1	0.0	629	regional
varmlandsbygden.se	1	0.0	470	regional
smbt.se	1	0.0	416	regional
skaraborgsbygden.se	1	0.0	648	regional
hoglandsnytt.se	1	0.0	1564	regional
tranas-posten.se	1	0.0	2310	local
skargarden.se	1	0.0	1364	local
firdatidend.no	1	0.0	181	local
molndalsposten.se	1	0.0	349	local
uppsalatidningen.se	1	0.0	300	local
http://minby.dk/oesterbro-avis/	1	0.0	438	local
bsnett.no	1	0.0	531	local
http://nyhende.komheim.no	1	0.0	333	local
aarsavis.dk	1	0.0	1915	local
kanukoka.gl	1	0.0	5886	regional
amliavisa.no	1	0.0	69	local
nsnet.dk	1	0.0	1	local
bmz.se	1	0.0	1	regional
velkomne.no	1	0.0	425	local
samso.dk	1	0.0	678	local
markbladet.se	1	0.0	1496	local
http://dinby.dk/frederiksvaerk-ugeblad	1	0.0	13	local
nyhetsbynleksand.se	1	0.0	439	local
kidsnews.dk	1	0.0	389	national
vaxjobladet.se	1	0.0	237	local
http://minby.dk/city-avisen/	2	0.0	476	local
http://minby.dk/valby-bladet/	2	0.0	511	local
http://www.stockholmdirekt.se/tabynyheter	2	0.0	12	local
http://www.direktpress.se/goteborg	2	0.0	754	local
http://www.stockholmdirekt.se/sodrasidan	2	0.0	19	local
http://www.stockholmdirekt.se/malarotidning	2	0.0	16	local
nordrenett.no	2	0.0	595	local
aasanetidende.no	2	0.0	1251	local
varingen.no	2	0.0	241	local
http://www.stockholmdirekt.se/enahabo	2	0.0	16	local
frostingen.no	2	0.0	344	local
statstidende.dk	2	0.0	8641
boblad.no	2	0.0	324	local
http://www.stockholmdirekt.se/kista-rinkeby-tensta	2	0.0	10	local
8sidor.se	2	0.045454545454545456	2063	national
selbyggen.no	2	0.0	515	local
vtb.no	2	0.0	155	local
naestved-bladet.dk	2	0.0	402	local
skive-her.dk	2	0.0	10281
brandebladet.dk	2	0.0	5730	local
hasserisavis.dk	2	0.0	392	local
orusttjorntidningen.se	2	0.0	169	local
tysnesbladet.no	2	0.0	531	local
drangedalsposten.no	2	0.0	733	local
sovesten.no	2	0.0	716	local
http://minby.dk/vesterbro-bladet/	2	0.0	426	local
http://www.stockholmdirekt.se/viisolna	2	0.0	12	local
austevollforlag.no	2	0.0	2885	local
ballerupbladet.dk	2	0.0	1732	local
nordschleswiger.dk	2	0.0	2534	local
synste.no	2	14.271759618404435	56	local
http://minby.dk/amagerbladet/	2	0.0	273	local
kjavis.dk	2	0.0	1935	local

This is local sites, (local 78, national2, regional 8,blank 2), more in denmark than the other (denmark 40, sweden 26, norway 24).

If we do the same with betweeness centrality, we get a list of 233 sites with 0. These are also mostly local (local184, regional26, national10, local/regional3, (blank)10) and slightly more danish. (denmark 121, norway 50, sweden 62)

Summary: It is quite normal for local news sites to be quite isolated. We might even say disconnected by choice, as it would be very easy to just add links.
(Discussion, do these only cover stuff that is not covered in the bigger regional/national sites, and thus not linkable within the pre-defined scope of our study?)

- who are systematically linking each other (more than once or twice)
    How do we define systematically? Is it a number threshold (e.g. more than 10 times)? Is it relative to the actor doing the linking (percent of all links to other sites in our sample is higher than n pr cent)? Is it relative to the number of internal links we have scraped to get the out links (nr of links to a particular actor divided by all outbound links including stuff outside our sample (I have the data for that)), or some other idea of "systematic"?
    - Can I refrace this to: What links are high in weight? (no)
    We have weighted the egdes, by the number of times a link from one node to another is made. Perhaps such a simple solution can suffice? (no)
    - Better: divide the weight on the n_internal (as a number of size of the news site) and get a likelyhood for that link. Then get top 10% of this new list. (penalizing sporadic linking)
    This I have added as a new attribute to the edges: w_over_internal

Ok. Så the systematic linking is the head of the long tail distribution of the w_over_internal attribute. Top 10% os ok?

There are 13406 edges.
The 1340th has w_over_internal 1.875
Adding filter  range(w_over_internal) 1,875 - max
Within the filter Degree ranger (more than 1, so we remove node without edges)
NB: Nested filters are applied with the most inner filter first, then the outer last. Odd, but true: http://www.clementlevallois.net/gephi/tuto/en/gephi_advanced%20functions_en.pdf

That gives us the network of truly systematic linking.
246 nodes, 1339 edges.
In Norway NRK stands out.
Some local clusters ({steinkjæravisa, inderøyningen.no, t-a.no}, {rbnett.no, smp.no}, {østlendingen, ringsakerblad} {rogalangs-klyngen, 9stk aviser})

In Sweden similar patter emerges: the stuff that is split up (like NRK) "holds together": {expressen.se x3, http://www.helahalsingland.se x4, allehanda x2, barometern.se x2, unt.se x2, dt.se x5, ekurinen.se x2, stockholmdirekt.se x7}
Some clusters includes other nodes than its own domain:
{nwt.se x9 this is also linked to sla.se and mariestadtidning.se}
{lindernytt.se, aftonbladet.se}
{vaxsjobladet.se, olandsbladet.se}
{partilletidning.se, alingsastidning.se, lerumstidning.se},

Denmark has 143 nodes satisfying these creteria. Much more than se and no.
With more nodes comes more complexity.
Some "normal" patterns emerge. Stuff that is split up clusters.
{nordjyske.dk x12, dr.dk x4, sn.dk x35, etc. }
And some "normal" smaller clusters, probably with the same owner:
{tv2.dk, mediawatch.dk, energiwatch.dk, medwatch.dk, finanswatch.dk, fodevarewatch.dk}
{aoh.dk, mja.dk, aoib.dk}
{b.dk, aok.dk, business.dk}
{fyens.dk x11, ugeavisensvendborg.dk, ugeavisen-odense.dk}
Then the complicated part:
{city}.lokalavise.dk makes a giant sub-network. It connetcts with jyllandsposten.dk and ekstrabladet.dk (but those two does not connect directly). This .localavisen.dk is probably this densely linked because of the CMS arcitecture, but in effect it connetcts Denamrk.
dinby.dk/{stuff} is not dense enough to show up as one network here, but in smaller clusters that connects with other things, such as amtsavisen.dk, dagbladet-holdterbro-struer.dk, dagbladetstringtjern.dk etc. This too might look like ownership.
Denmark should probably be studies closer because of its more chaotic stucture with dinby and lokalavisen.


Answer: By looking at the 10% strongest ties as a representation for systematic linking, we find newsrooms within the same brands and what looks like the same owers (not tested).

This question can be explored more bye looking at 20-10% range, to see what the second tire looks like, that's propably where we find the "newsworthiness"-linking (where links are made because of some newsroom setting the agenda, and others linking to them to connect to the current agenda)


- Does location in a mayor city help network centrality?
- Does local news sites connect their readers to the larger national disqorses?
- does the big hubs link out to the local
    Filter on betweenes centality, then inter egdes on level.
   BC does not seem to show up in any filters, so I use degree. That should give aprox the same central nodes.
   Degree range(100-307) +  
- can I find the "umbrella-structre" from Helles theories?
- to what extent are the countries connected?
    Filters: range(w_over_internal) + inter Edeges (countries) + degree (1 or more) Gives all nodes that still has edges that cross a border, where a certain w_over_range threshold is meat.
    With no threshold 37,8% of the nodes has a link across country borders, 9,32% of all edges. That is more than expected. But: this is just edges, we have to include weight in order for this to sober up.
    The once of these edges that occur more than 10 times makes 209, and of these the top 46 are from {place}.lokaltidningen.se to ekstrabladet.dk or politiken.dk (same owner?).
    The degree of the network goes down to 2,27. We are much less densely connected. A typical site that does link across countries, only reaches 2.27 sites across a border. That is about a a 10th as connected as it is within its own country. But: still more than I had expected.
    Of these 209 we check on In-Degree and Out-degree. This tells us who links more out (active across borders, international mindset) and who are linked to (relevance across borders). The out-degree (more different links across borders) top list is:
    ing.dk, dagbladet.no, informasjonen.dk, modkraft.dk, aftenposten.no, vg.no, dn.no, dagen.no, adressa.no, bohuslaningen.se, bt.dk and aftonbladet.se (all have 5 or more in out-degree in this subset.)
    The biggest in-degree (are seen as relevant across borders) politiken.dk, akstrabladet.dk, expressen.se, aftonbladet.se, dn.se, vg.no svd.se, bt.dk, aftenposten.no and dagbladet.no (with 6 or more links across countries)
    At range(w_over_internal) 2: we only have politiken.dk and ekstrabladet.dk from denmark linked with sweden though {place}.lokaltidkningen.se
    0,01 gives 39 nodes (5.8% of the network) and 56 egdes (0.42% of edges)

    <!-- Links has weight 10 (10 times linked)
    1000 documents in my site
    w_over_internal = 10/1000 -> 0,01 -->
    Threshold 0,01 (links that happens 1 time pr 100 documents/articles) gives 39 nodes (5.8% of the network) and 56 egdes (0.42% of edges) that link across country one time pr 100 produced articles.

    39 sites does does meet this requirement, that is more than what I
- Does the regional paper connect the local and national?

## Questions picked up from abstracts
- RQ: How/to what extent are the local, regional & national sites connected?
    - Network density. How far are the subnetworks (no/se/dk) across?
    - Do national connect more with national, regional & local?
    - Do we find isolated "islands" of sites?
- RQ: Who are the hubs in the Scandinavian news ecology? What do they connect to? What barriers do the cross?
    - Who in total, and who pr country take the role as central players?
    - Do these link more to international/national/regional/local?
    - Are they similar across countries?

- RQ: What is typical about the local news sites in the network?
    - inn links vs out links
    - number of national/regional to local links

- RQ: What describes the hubs in the network? Are the big city nationals only? Do the connect mostly with other nationals and regionals, or do the connect "all the way down"?
    - Are the hub only in big cities/capitals?
    - Do the big players link to local, or more to the regional?
    - Are any hubs regional/local, or only national?

- RQ: If we filter the graph pr country, do we find the same national/regional/local patterns en all countries? Do the hubs stay the same?


- RQ: Is the major linking highways between nr1 and nr2 city in all countries?

- RQ: Are the major linking highways between the major news outlets?

- RQ: To what extent do we find linking across national borders? If any, what describes this king of linking?

- RQ: In the capitals, do we find more links out than inn, in total?

- Do local newspaper get linked more than they link out themselves?
