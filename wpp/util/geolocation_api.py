#!/usr/bin/env python
import sys
import os
import csv
import time
import urllib2 as ul
import socket as sckt
import numpy as np
import pprint as pp
import simplejson as json
import sqlite3 as db
#import logging
#wpplog = logging.getLogger('wpp')
from wpp.config import termtxtcolors as colors
 

def genLocReq(macs=None, rsss=None, cellinfo={}, atoken=None):
    """
    Request format:
    {
      "version": "1.1.0",
      "host": "maps.google.com",
      "access_token": "2:k7j3G6LaL6u_lafw:4iXOeOpTh1glSXe",
      "home_mobile_country_code": 310,
      "home_mobile_network_code": 410,
      "radio_type": "gsm",
      "carrier": "Vodafone",
      "request_address": true,
      "address_language": "en_GB",
      "location": {
        "latitude": 51.0,
        "longitude": -0.1
      },
      "cell_towers": [
        {
          "cell_id": 42,
          "location_area_code": 415,
          "mobile_country_code": 310,
          "mobile_network_code": 410,
          "age": 0,
          "signal_strength": -60,
          "timing_advance": 5555
        }, ],
      "wifi_towers": [
        {
          "mac_address": "01-23-45-67-89-ab",
          "signal_strength": 8,
          "age": 0
        },
      ]
    }
    Response format:
    {
      "location": {
        "latitude": 51.0,
        "longitude": -0.1,
        "altitude": 30.1,
        "accuracy": 1200.4,
        "altitude_accuracy": 10.6,
        "address": {
          "street_number": "100",
          "street": "Amphibian Walkway",
          "postal_code": "94043",
          "city": "Mountain View",
          "county": "Mountain View County",
          "region": "California",
          "country": "United States of America",
          "country_code": "US"
        }
      },
      "access_token": "2:k7j3G6LaL6u_lafw:4iXOeOpTh1glSXe"
    }
    """
    req = {}; cellinfo_keys = cellinfo.keys()
    if 'lac' in cellinfo_keys and 'cid' in cellinfo_keys:
        lac = cellinfo['lac']; cid = cellinfo['cid']
        req['cell_towers'] = [ { 'cell_id':cid, 'location_area_code':lac} ]
        if 'rss' in cellinfo_keys: req['cell_towers'][0]['signal_strength'] = cellinfo['rss']
    req['mobile_country_code'] = cellinfo['mcc'] if ('mcc' in cellinfo_keys) else 460 
    req['mobile_network_code'] = cellinfo['mnc'] if ('mnc' in cellinfo_keys) else 0
    if len(macs): req['wifi_towers'] = [{'mac_address':m, 'signal_strength':rsss[i]} for i,m in enumerate(macs)]
    req['version'] = '1.1.0'
    if atoken: req['access_token'] = atoken
    req_json = json.dumps(req)
    return req_json


def connect_retry(**ka):
    """ try 10 times at most. """
    def decorator(f, **kb):
        def wrapper(*args, **kc):
            delay = 1; result = None
            if 'try_times' in ka and type(ka['try_times']) is int: try_times = ka['try_times']
            else: try_times = 5
            for i in xrange(try_times):
                try:
                    result = f(*args, **kc)
                    break
                except (sckt.error, ul.URLError), e:
                    if hasattr(e, 'code'):
                        print(colors['red'] % ('HTTP Error: (%s): %s' % (e.code, e.msg)))
                    elif hasattr(e, 'reason'):
                        print(colors['red'] % ('URL Error: %s!' % e.reason))
                    else: print e
                except Exception, e: print e
                delay += 0.5; time.sleep(delay)
                print colors['blue'] % '... Retrying ...'
            return result
        return wrapper
    return decorator

@connect_retry(try_times=3)
def googleLocation(macs=[], rsss=[], cellinfo=None):
    req_content = genLocReq(macs=macs, rsss=rsss, cellinfo=cellinfo)
    req_url = "http://www.google.com/loc/json"
    sckt.setdefaulttimeout(3)#; setProxy()
    resp = ul.urlopen(req_url, req_content)
    ret_content = dict( eval(resp.read()) )
    if not 'location' in ret_content: return []
    gloc = ret_content['location'] 
    if gloc['accuracy'] > 5000: return []
    gh = gloc['altitude'] if ('altitude' in gloc) else 0
    return [ gloc['latitude'], gloc['longitude'], gh, gloc['accuracy'] ]


def setProxy():
    proxyserver = "http://proxy.cmcc:8080"
    proxy = {'http': proxyserver}
    #sckt.setdefaulttimeout(50)
    opener = ul.build_opener( ul.ProxyHandler(proxy) )
    ul.install_opener( opener )


@connect_retry()
def googleGeocoding(latlon=(0,0), format='json', sensor='false'):
    """return reverse geocoding result of google api."""
    googleurl = 'http://maps.google.com/maps/api/geocode'
    uri = '%s/%s?latlng=%s,%s&sensor=%s' % (googleurl,format,latlon[0],latlon[1],sensor)
    resp = ul.urlopen(uri)
    data = json.load(resp)
    return data

def collectCellArea():
    query_cnt = 0 # Google Map API regular user limit: no more than 2500 queries/day
    cell_area = {}
    homedir = os.environ['HOME']; csvfile = '%s/wpp/wpp/util/cells_latlon.csv' % homedir
    conn = db.connect('%s/wpp/wpp/util/cell_area.db'% homedir); cur = conn.cursor()
    cells_loc = open(csvfile,'r').readlines()
    for cell in cells_loc:
        lac,cid,lat,lon = [ x.strip('\"') for x in cell.strip().split(',') ]
        print '%s, %s, %s, %s' % (lac, cid, lat, lon)
        sql = 'SELECT areacode from cell_area WHERE lac=%s AND cellid=%s'%(lac,cid)
        cur.execute(sql)
        areacodes = cur.fetchall()
        if not areacodes:
            latlon = (lat, lon)
            geodata = googleGeocoding(latlon)
            if type(geodata) is dict and 'status' in geodata:
                if geodata['status'] == u'OK':
                    query_cnt += 1; print 'query count: %s' % query_cnt
                    # filter out sublocality field.
                    area_names = [ x['address_components'][::-1][1:] 
                            for x in geodata['results'] if x['types'][0]=='sublocality' ]
                    if area_names: area_names = area_names[0]
                    else: # if no sublocality presented, then filter out street_address field.
                        area_names = [ x['address_components'][::-1][:-2] 
                                for x in geodata['results'] if x['types'][0]=='street_address' ]
                        if area_names: area_names = area_names[0]
                        else: continue
                    area_name = [ x['long_name'] for x in area_names if not x['long_name'].isdigit() ]
                    area_district = area_name[-1]
                    if not area_district in area_codes: 
                        print 'district: %s not in area_codes!' % area_district
                        pp.pprint(geodata['results']); sys.exit(0)
                    area_code = area_codes[area_district]
                    if area_code in [x[0] for x in areacodes]: continue
                    area_name = '+'.join(area_name)
                    rec = '"%s","%s","%s","%s"' % (cid, area_code, area_name, lac)
                    cur.execute('INSERT INTO cell_area VALUES (%s)' % rec)
                    conn.commit()
                    print colors['blue'] % ('insert %s' % rec)
                else: sys.exit(colors['red'] % ('ERROR: %s !!!' % geodata['status']))
            else: print colors['red'] % 'ERROR: Geocoding Failed !!!'; continue
        else: continue
        cur.execute('select count(*) from cell_area')
        print 'Count: %s\n%s' % (cur.fetchone()[0], '-'*40)
    conn.close()


area_codes = {
      "Dongcheng": "110101",
        "Xicheng": "110102",
       "Chongwen": "110103",
         "Xuanwu": "110104",
       "Chaoyang": "110105",
        "Fengtai": "110106",
    "Shijingshan": "110107",
        "Haidian": "110108",
      "Mentougou": "110109",
       "Fangshan": "110111",
       "Tongzhou": "110112",
         "Shunyi": "110113",
      "Changping": "110114",
         "Daxing": "110115",
        "Huairou": "110116",
         "Pinggu": "110117",
          "Miyun": "110228",
        "Yanqing": "110229",
          "Mawei": "350105",
        "Changle": "350182",
          "Gulou": "350102",
         "Jin'an": "350111",
       "Taijiang": "350103",
       "Cangshan": "350104",
        "Kunshan": "320583",
        "Beitang": "320204",
       "Chong'an": "320202",
       "Nanchang": "320203",
          "Anxin": "130632",
     "Gaobeidian": "130684",
       "Zhuozhou": "130681",
       "Dingxing": "130626",
      "Rongcheng": "130629",
         "Xushui": "130625",
         "Jixian": "120225",
       "Dongling": "210112",
          "Daoli": "230102",
       "Jinjiang": "350582",
       "Changtai": "350625",
       "Kongtong": "620802",
           "Jimo": "370282",
         "Shibei": "370203",
         "Sifang": "370205",
          "Yanta": "610113",
        "Chiping": "371523",
       "Qingyang": "510105",
      "Pingjiang": "430626",
         "Jiyuan": "419001",
         "Tianhe": "440106",
       "Bao'anqu": "440306",
         "Xishan": "320205",
        "Fucheng": "510703",
        "Youxian": "510704",
         "Hal'an": "320621",
          "Laixi": "370285",
         "Nanhai": "440605",
           "Anji": "330523",
       "Jiangbei": "330205",
         "Doumen": "440403",
      "Jiangning": "320115",
       "Jiangyan": "321284",
         "Shishi": "350581",
        "Shifang": "510682",
          "Jinxi": "361027",
        "Jiading": "310114",
   "Huangshigang": "420202",
         "Qingpu": "310118",
       "Dangyang": "420582",
     "Tianbao Rd": "441900",
     "Jiangchuan": "530421",
        "Qinhuai": "320104",
      "Shouguang": "370783",
       "Shahekou": "210204",
      "Shuimogou": "650105",
          "Pukou": "320111",
         "Tinghu": "320902",
         "Lianhu": "610104",
          "Qixia": "320113",
      "Tai Ha St": "810000",
        "Sha Tin": "810000",
     "Pak Tak St": "810000",
         "Jinnan": "120112",
        "Jinshui": "410105",
          "Panyu": "440113",
         "Heping": "210102",
        "Wucheng": "330702",
        "Jing'an": "310106",
     "Tin Wah Rd": "810000",
       "Shiji Rd": "210100",
 "Hunnan West Rd": "210100",
    "Shenying Rd": "210100",
     "Xinlong St": "210100",
       "Gaoge Rd": "210100",
       "Gaoke Rd": "210100",
"Changbai East Rd": "210100",
"Changbai West Rd": "210100",
      "Minzhu Rd": "210100",
      "Nansan Rd": "210100",
    "Tongze S St": "210100",
   "Tianjin S St": "210100",
     "Nansima Rd": "210100",
   "Nanning S St": "210100",
     "River N St": "210100",
      "Yuping Rd": "210100",
     "Nanyima Rd": "210100",
    "Heping S St": "210100",
    "Zhonghua Rd": "210100",
       "Shenyang": "210100",
         "Haizhu": "440105",
        "Gucheng": "530702",
      "Songjiang": "310117",
        "Minhang": "310112",
        "Wanzhou": "500101",
         "Futian": "440304",
       "Xingning": "441481",
        "Weiyang": "610112",
       "Lingling": "431102",
    "Lengshuitan": "431103",
       "Baiyunqu": "440111",
          "Liwan": "440103",
         "Shunde": "440606",
      "Anningshi": "530181",
          "Yubei": "500112",
         "Anyang": "410500",
        "Hanshan": "341423",
        "Lanshan": "371302",
        "Tianxin": "430103",
          "Putuo": "310107",
          "Huadu": "440114",
         "Haishu": "330203",
         "Shinan": "370202",
         "Zhabei": "310108",
          "Guide": "632523",
        "Xianyou": "350322",
        "Hongkou": "310109",
        "Dongtai": "320981",
        "Laizhou": "370683",
         "Yangpu": "310110",
        "Jindong": "330703",
       "Pengshui": "500243",
      "Yongchuan": "500118",
        "Wuzhong": "320506",
       "Beilinqu": "610103",
    "Hami(Kumul)": "652201",
      "Jiangdong": "330204",
       "Huangdao": "370211",
           "Daye": "420281",
           "Wudi": "371623",
          "Feixi": "340123",
          "Lixia": "370102",
         "Liandu": "331102",
         "Linwei": "610502",
         "Qiaoxi": "130104",
        "Xinzhou": "420117",
        "Dinghai": "330902",
        "Changji": "652301",
        "Yingkou": "210800",
      "Shuangliu": "510122",
      "Shayibake": "650103",
       "Fengyang": "341126",
    "Xixiangtang": "450107",
          "Taihe": "360826",
          "Wujin": "320412",
     "Jiangcheng": "530826",
 "Jiangzhou Unit": "451402",
         "Hui'an": "350521",
   "Pudong Xinqu": "310115",
   "Binhai Xinqu": "120116",
          "Binhu": "320211", }

if __name__ == "__main__":
    try:
        import psyco
        psyco.bind(genLocReq)
        #psyco.bind(googleLocation)
        psyco.bind(setProxy)
        #psyco.bind(googleGeocoding)
    except ImportError:
        pass

    #setProxy()
    
    collectCellArea()

    sys.exit(0)
    #wlans = ['00:21:91:1D:C0:D4|00:27:19:88:97:10|00:19:E0:CC:9C:F8|00:23:CD:54:DC:E0','-83|-86|-85|-88']
    #macs = wlans[0].split('|')
    #rsss = wlans[1].split('|')
    #wlans = []
    #for i,mac in enumerate(macs):
    #    wlan = {}
    #    wlan['mac_address'] = mac
    #    wlan['signal_strength'] = rsss[i]
    #    wlans.append(wlan)
    #print wlans

    # csvfile format: x,y,lac,cid
    csvfile = sys.argv[1] 
    csvin = csv.reader( open(csvfile,'r') )
    laccids = np.array([ line for line in csvin ])[:,2:].astype(int)
    print laccids

    atoken = None; celldb = []
    for i,laccid in enumerate(laccids):
        print '-'*50
        cell = {}
        cell['location_area_code'] = laccid[0]
        cell['cell_id'] = laccid[1]
        cells = [ cell ]
        req_content = genLocReq(cells=cells, atoken=atoken)
        print '%d: %s' % (i+1, json.loads(req_content)['cell_towers'])
        ret_content = googleLocation(req_content)
        if not len(ret_content): 
            print colors['red'] % 'Google location failed!'
            continue
        if ret_content['location']['accuracy'] >= 1000: 
            print colors['red'] % 'Accuracy too bad!'
            continue
        cdb = [ str(laccid[0]), str(laccid[1]),
                str(ret_content['location']['latitude']), 
                str(ret_content['location']['longitude']),
                str(ret_content['location']['accuracy']) ]
        if (not atoken) and ('access_token' in ret_content):
            atoken = ret_content['access_token']
        celldb.append(cdb)
        print '%d: %s' % (len(celldb), cdb)

    timestamp = time.strftime('%Y%m%d-%H%M%S')
    datafile = 'celldb_%s.csv' % timestamp
    celldb = np.array(celldb)
    np.savetxt(datafile, celldb, fmt='%s',delimiter=',')
    print '\nDumping all celldb to: %s ... Done' % datafile
