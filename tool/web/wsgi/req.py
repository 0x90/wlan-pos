#!/usr/bin/env python
import sys
import os
import urllib2, urllib
path_repo = os.path.split(os.path.abspath(__file__))[0] + '/../../../'
sys.path.append(path_repo)
sys.path.append(path_repo+'tool')

#data = {'name' : 'yxt', 'password' : 'pwd'}
req_wpp = """<?xml version="1.0"?><!DOCTYPE PosReq SYSTEM "PosReq.dtd"><PosReq><SPID val="123" /><ServID val="456" /><Time val="20110130-114424" /><UserInfo imei="355302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" /><CellInfo mcc="460" mnc="00" lac="4577" cid="3088" rss="-63" /><WLANIdentifier val="00:15:70:9f:62:64|00:25:86:4a:b9:6e|00:15:70:9f:72:0c|00:15:70:d0:52:60|00:23:cd:68:f6:d6|00:1b:11:a4:2d:c6|00:15:70:a6:a3:30|00:15:70:9f:62:66|00:15:70:9f:72:0e|00:15:70:d0:52:62|00:25:86:51:bd:54|00:15:70:a6:a3:32|00:1c:10:aa:c0:a8|00:11:b5:fd:76:d4" /><WLANMatcher val="-40|-61|-70|-72|-75|-85|-85|-40|-69|-72|-82|-84|-88|-59" /></PosReq>"""
req_fpp = """<?xml version="1.0"?><!DOCTYPE PosReq_FC SYSTEM "PosReq_FC.dtd"><PosReq_FC><SPID val="123" /><ServID val="456" /><Time val="20110130-114424" /><UserInfo imei="355302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" /><CellInfo mcc="460" mnc="00" lac="4577" cid="3088" rss="-63" /><WLANIdentifier val="00:15:70:9f:62:64|00:25:86:4a:b9:6e|00:15:70:9f:72:0c|00:15:70:d0:52:60|00:23:cd:68:f6:d6|00:1b:11:a4:2d:c6|00:15:70:a6:a3:30|00:15:70:9f:62:66|00:15:70:9f:72:0e|00:15:70:d0:52:62|00:25:86:51:bd:54|00:15:70:a6:a3:32|00:1c:10:aa:c0:a8|00:11:b5:fd:76:d4" /><WLANMatcher val="-40|-61|-70|-72|-75|-85|-85|-40|-69|-72|-82|-84|-88|-59" /></PosReq_FC>"""
resp_xml = """<?xml version ="1.0"?><!DOCTYPE PosRes SYSTEM "PosRes.dtd"><PosRes><Result ErrCode="100" ErrDesc="OK"/><Coord lat="39.894943" lon="116.345218" h="42.000000"/><ErrRange val="27.84"/></PosRes>]"""


if __name__ == "__main__":
    from evaloc import getIPaddr
    ipsrc = getIPaddr()
    #ipserver = '192.168.109.48'
    #ipserver = '192.168.109.51'
    #ipserver = '192.168.109.56'
    #ipserver = '192.168.109.58'
    ipserver = '192.168.0.100'
    if 'wlan0' in ipsrc:
        ipsrc = ipsrc['wlan0']
    else:
        ipsrc = ipsrc['eth0']
    port = '18080'
    #port = '8080'
    #path_info = 'fpp_ad/adapter'
    path_info = 'wlan/distribution'
    url_server = 'http://%s:%s/%s' % (ipserver, port, path_info)
    print 'Requesting %s from %s' % (url_server, ipsrc)
    print req_wpp

    #req = urllib2.Request(url=url_server, data=urllib.urlencode(data))
    req = urllib2.Request(url=url_server, data=req_wpp)
    resp = urllib2.urlopen(req)
    print '-'*40
    print 'Response:'
    print resp.code, resp.read()
