#!/usr/bin/env python
import sys
import csv
import urllib2 as ul
import socket as sckt
import numpy as np
import pprint as pp
import simplejson as json
 

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


def getGL(req_content=None):
    # Note: Currently urllib2 does not support fetching of https locations through a proxy. 
    # However, this can be enabled by extending urllib2 as shown in the recipe:
    # http://code.activestate.com/recipes/456195.
    req_url = "http://www.google.com/loc/json"
    if not req_content:
        sys.exit('Error: EMPTY request content!')
    while True:
        try:
            resp = ul.urlopen(req_url, req_content)
            ret_content = dict( eval(resp.read()) )
            break
        except ul.URLError, e:
            if hasattr(e, 'code'):
                print('HTTP Error: (%s): %s' % (e.code, e.msg))
            elif hasattr(e, 'reason'):
                print('URL Error: %s!' % e.reason)
            else: print e
        print '... Retrying ...'
    return ret_content


def setConn():
    proxyserver = "http://proxy.cmcc:8080"
    proxy = {'http': proxyserver}
    #sckt.setdefaulttimeout(50)

    opener = ul.build_opener( ul.ProxyHandler(proxy) )
    ul.install_opener( opener )


if __name__ == "__main__":
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

    #setConn()

    atoken = None; celldb = []
    for i,laccid in enumerate(laccids):
        cell = {}
        cell['location_area_code'] = laccid[0]
        cell['cell_id'] = laccid[1]
        cells = [ cell ]
        req_content = makeReq(cells=cells, atoken=atoken)
        pp.pprint(req_content['cell_towers'])
        ret_content = getGL(req_content)
        if not len(ret_content): 
            print 'Google location failed!'
            continue
        if ret_content['location']['accuracy'] >= 1000: 
            print 'Accuracy too bad!'
            continue
        cdb = [ str(laccid[0]), str(laccid[1]),
                str(ret_content['location']['latitude']), 
                str(ret_content['location']['longitude']),
                str(ret_content['location']['accuracy']) ]
        if (not atoken) and ('access_token' in ret_content):
            atoken = ret_content['access_token']
        celldb.append(cdb)
        print '%d: %s' % (i+1, cdb)
        print

    datafile = 'celldb.csv'
    celldb = np.array(celldb)
    np.savetxt(datafile, celldb, fmt='%s',delimiter=',')
    print '\nDumping all req/ret/err to: %s ... Done' % datafile
