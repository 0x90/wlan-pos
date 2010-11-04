#!/usr/bin/env python
import sys
import urllib2 as ul
import socket as sckt
import pprint as pp
 

def makeReq(wlan=None, atoken=None):
    if wlan:
        macs = wlan[0]
        rsss = wlan[1]
        wifis = []
        for x in xrange(len(macs)):
            wifi = '{"mac_address":"%s", "signal_strength":%s}' % (macs[x], rsss[x])
            wifis.append(wifi)
        wifis = ','.join(wifis)
    else:
        wifis = ""
    req_content = """
    {
    "version":"1.1.0",
    "access_token":"%s",
    "wifi_towers":
    [
    %s
    ]
    }
    """ % (atoken, wifis)

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
            sys.stdout.write('Error: %s!' % e)
            print ' ...Retrying...'
    return ret_content


def setConn():
    proxyserver = "http://proxy.cmcc:8080"
    proxy = {'http': proxyserver}
    #sckt.setdefaulttimeout(50)

    opener = ul.build_opener( ul.ProxyHandler(proxy) )
    ul.install_opener( opener )


if __name__ == "__main__":
    wlan = ['00:21:91:1D:C0:D4|00:27:19:88:97:10|00:19:E0:CC:9C:F8|00:23:CD:54:DC:E0','-83|-86|-85|-88']
    macs = wlan[0].split('|')
    rsss = wlan[1].split('|')
    wlan = [ macs, rsss ]

    req_content = makeReq(wlan=wlan)
    ret_content = getGL(req_content)
    pp.pprint(ret_content)

    if 'access_token' in ret_content:
        atoken = ret_content['access_token']
        req_content = makeReq(wlan=wlan,atoken=atoken)
        ret_content = getGL(req_content)
        pp.pprint(ret_content)
