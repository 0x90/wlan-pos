#!/usr/bin/env python
import sys
import csv
import time
import urllib2 as ul
import socket as sckt
import numpy as np
import pprint as pp
import simplejson as json
import sqlite3 as db
from wpp.config import termtxtcolors as colors
 

def makeReq(wlans=None, cells=None, atoken=None):
    """
    wlans: Old, [ [ mac1, mac2, ...], [rss1, rss2, ...] ]
    wlans: New, [ wifi1, wifi2, ...]
        wifiX: {"mac_address":"aa", "signal_strength":yy, ...}
    cells: [ cell1, cell2, ... ]
        cellX: {"cell_id":xxx, "location_area_code":yyy, ...}
    """
    # Old.
    # FIXME: refactor with simplejson.dumps(dict)
    #if wlans:
    #    macs = wlans[0]; rsss = wlans[1]; wifis = []
    #    for x in xrange(len(macs)):
    #        wifi = '{"mac_address":"%s", "signal_strength":%s}' % (macs[x], rsss[x])
    #        wifis.append(wifi)
    #    wifis = ','.join(wifis)
    #else:
    #    wifis = ""
    #req_content = """
    #{
    #"version":"1.1.0",
    #"access_token":"%s",
    #"wifi_towers":
    #[
    #%s
    #]
    #}
    #""" % (atoken, wifis)

    # New.
    req_content = {}
    if (type(cells) is list) and ( len(cells) ):
        req_content['cell_towers'] = cells
        req_content['mobile_country_code'] = 460
        req_content['mobile_network_code'] = 0

    if (type(wlans) is list) and ( len(wlans) ):
        req_content['wifi_towers'] = wlans

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
            except ul.URLError, e:
                if hasattr(e, 'code'):
                    print(colors['red'] % ('HTTP Error: (%s): %s' % (e.code, e.msg)))
                elif hasattr(e, 'reason'):
                    print(colors['red'] % ('URL Error: %s!' % e.reason))
                else: print e
            print colors['blue'] % '... Retrying ...'
        return result
    return wrapper

@connect_error
def getGL(req_content=None):
    # Note: Currently urllib2 does not support fetching of https locations through a proxy. 
    # However, this can be enabled by extending urllib2 as shown in the recipe:
    # http://code.activestate.com/recipes/456195.
    req_url = "http://www.google.com/loc/json"
    if not req_content: sys.exit('Error: EMPTY request content!')
    resp = ul.urlopen(req_url, req_content)
    return dict( eval(resp.read()) )


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
    cell_area = {}
    csvfile = '/home/alexy/wpp/dat/fpp_rawdata/cells_latlon.csv'
    cells = open(csvfile,'r').readlines()
    conn = db.connect('/home/alexy/dev/src/wpp/dat/cell_area.db')
    cur = conn.cursor()
    #cur.execute('create table cell_area (cellid char(15) not null, areacode char(15) not null, areaname char(50))')
    for cell in cells:
        #print cell
        cid,lat,lon = cell.strip().split(',')
        cur.execute('SELECT areacode from cell_area WHERE cellid LIKE %s' % cid)
        areacodes = cur.fetchall()
        if not areacodes:
            latlon = (lat, lon)
            geodata = googleGeocoding(latlon)
            area_name = [ x['long_name'] for x in geodata['results'][1]['address_components'][::-1][1:] ]
            area_district = area_name[-1]
            if not area_district in area_codes: continue
            area_code = area_codes[area_district]
            if area_code in [x[0] for x in areacodes]: continue
            area_name = '|'.join(area_name)
            sql = 'INSERT INTO cell_area VALUES ("%s","%s","%s")' % (cid, area_code, area_name)
            cur.execute(sql)
            conn.commit()
            print sql
        else: continue
        cur.execute('select count(*) from cell_area')
        print 'Count: %s' % cur.fetchone()[0]
        print '-'*40
    conn.close()


if __name__ == "__main__":
    try:
        import psyco
        psyco.bind(makeReq)
        #psyco.bind(getGL)
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
          'Shangping': '110114',
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
        req_content = makeReq(cells=cells, atoken=atoken)
        print '%d: %s' % (i+1, json.loads(req_content)['cell_towers'])
        ret_content = getGL(req_content)
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
