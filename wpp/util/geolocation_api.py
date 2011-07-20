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
import functools
from wpp.config import termtxtcolors as colors
 

def genLocReq(macs=None, rsss=None, lac=None, cid=None, cellrss=None, atoken=None):
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
    req_content = {}
    if lac and cid:
        req_content['cell_towers'] = [ { 'cell_id': cid, 'location_area_code': lac} ]
        if cellrss: req_content['cell_towers'][0]['signal_strength'] = cellrss
        req_content['mobile_country_code'] = 460
        req_content['mobile_network_code'] = 0

    if (type(macs) is list) and ( len(macs) ):
        wifi_towers = [ {'mac_address': mac, 'signal_strength': rsss[i]} for i,mac in enumerate(macs) ]
        req_content['wifi_towers'] = wifi_towers

    req_content['version'] = '1.1.0'
    if atoken: req_content['access_token'] = atoken
    req_content = json.dumps(req_content)
        
    return req_content


def connect_error(f):
    def wrapper(*arg, **ka):
        while True:
            try:
                result = f(*arg, **ka)
                break
            except (sckt.error, ul.URLError), e:
                if hasattr(e, 'code'):
                    print(colors['red'] % ('HTTP Error: (%s): %s' % (e.code, e.msg)))
                elif hasattr(e, 'reason'):
                    print(colors['red'] % ('URL Error: %s!' % e.reason))
                else: print e
            except Exception, e:
                print e
            print colors['blue'] % '... Retrying ...'
            #if isinstance(retry, int):
            #    if retry <= 0: break
            #    else: retry -= 1
        return result
    return wrapper

@connect_error
def googleLocation(macs=None, rsss=None, lac=None, cid=None, cellrss=None):
    # Note: Currently urllib2 does not support fetching of https locations through a proxy. 
    # However, this can be enabled by extending urllib2 as shown in the recipe:
    # http://code.activestate.com/recipes/456195.
    req_content = genLocReq(macs=macs, rsss=rsss, lac=lac, cid=cid, cellrss=cellrss)
    req_url = "http://www.google.com/loc/json"
    if not req_content: sys.exit('Error: EMPTY request content!')
    print req_content
    sckt.setdefaulttimeout(5)
    resp = ul.urlopen(req_url, req_content)
    ret_content = dict( eval(resp.read()) )
    if not len(ret_content) or (ret_content['location']['accuracy'] >= 1000): 
        print colors['red'] % 'Google location failed!'
        return []
    else:
        return [ ret_content['location']['latitude'], 
                 ret_content['location']['longitude'], 
                 ret_content['location']['accuracy'] ]


def setConn():
    proxyserver = "http://proxy.cmcc:8080"
    proxy = {'http': proxyserver}
    #sckt.setdefaulttimeout(50)
    opener = ul.build_opener( ul.ProxyHandler(proxy) )
    ul.install_opener( opener )


@connect_error
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
            if geodata['status'] == u'OK':
                query_cnt += 1; print 'query count: %s' % query_cnt
                area_names = [ x['address_components'][::-1][1:]
                        for x in geodata['results'] if x['types'][0]=='sublocality' ][0]
                area_name = [ x['long_name'] for x in area_names ]
                area_district = area_name[-1]
                if not area_district in area_codes: 
                    print 'district: %s not in area_codes!' % area_district
                    pp.pprint(geodata['results']); sys.exit(0)
                area_code = area_codes[area_district]
                if area_code in [x[0] for x in areacodes]: continue
                area_name = '|'.join(area_name)
                rec = '"%s","%s","%s","%s"' % (cid, area_code, area_name, lac)
                cur.execute('INSERT INTO cell_area VALUES (%s)' % rec)
                conn.commit()
                print colors['blue'] % ('insert %s' % rec)
            else: sys.exit(colors['red'] % ('ERROR: %s !!!' % geodata['status']))
        else: continue
        cur.execute('select count(*) from cell_area')
        print 'Count: %s\n%s' % (cur.fetchone()[0], '-'*40)
    conn.close()


if __name__ == "__main__":
    try:
        import psyco
        psyco.bind(genLocReq)
        #psyco.bind(googleLocation)
        psyco.bind(setConn)
        #psyco.bind(googleGeocoding)
    except ImportError:
        pass

    area_codes = {
          'Dongcheng': '110101',
            'Xicheng': '110102',
           'Chongwen': '110103',
             'Xuanwu': '110104',
           'Chaoyang': '110105',
            'Fengtai': '110106',
        'Shijingshan': '110107',
            'Haidian': '110108',
          'Mentougou': '110109',
           'Fangshan': '110111',
           'Tongzhou': '110112',
             'Shunyi': '110113',
          'Changping': '110114',
             'Daxing': '110115',
            'Huairou': '110116',
             'Pinggu': '110117',
              'Miyun': '110228',
            'Yanqing': '110229', }

    #setConn()
    
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
