#!/usr/bin/env python
import sys
import os
import urllib2
#import urllib
#import zlib

from wpp.util.net import getIP

# ERROR: Following 2 totally different req data used to have the same WLAN location result.
#req_wpp = """<?xml version='1.0' encoding='UTF-8' standalone='no' ?><!DOCTYPE PosReq SYSTEM "PosReq.dtd"><PosReq><SPID val="1000" /><ServID val="1000110" /><Time val="20110907-072248" /><UserInfo imei="352284040778213" imsi="460001343119748" UserAgent="Samsung/OMAP_SS" /><CellInfo mcc="460" mnc="00" lac="4141" cid="56479" rss="-49" /><WLANIdentifier val="00:24:b2:a6:74:28|d8:5d:4c:50:42:96|00:17:7b:0f:0f:58" /><WLANMatcher val="-87|-88|-88" /><PosLevel val="Point" /></PosReq>"""
req_wpp = """<?xml version='1.0' encoding='UTF-8' standalone='no' ?><!DOCTYPE PosReq SYSTEM "PosReq.dtd"><PosReq><SPID val="1000" /><ServID val="1000110" /><Time val="20110905-214442" /><UserInfo imei="352284040778213" imsi="460001343119748" UserAgent="Samsung/OMAP_SS" /><CellInfo mcc="460" mnc="00" lac="4607" cid="2085" rss="-49" /><WLANIdentifier val="00:14:5a:01:54:52|00:14:5a:01:55:73|00:14:5a:01:53:4a|00:14:5a:01:55:55|00:14:5a:01:55:6f" /><WLANMatcher val="-73|-76|-79|-90|-91" /><PosLevel val="Point" /></PosReq>"""
# WLAN FAIL.
#req_wpp = """<?xml version="1.0"?><!DOCTYPE PosReq SYSTEM "PosReq.dtd"><PosReq><SPID val="123" /><ServID val="456" /><Time val="20110130-114424" /><UserInfo imei="355302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" /><CellInfo mcc="460" mnc="00" lac="4577" cid="3088" rss="-63" /><WLANIdentifier val="00:15:70:9f:62:6a" /><WLANMatcher val="-40" /></PosReq>"""
# WPP OK, PosLevel = Point.
#req_wpp = """<?xml version='1.0' encoding='UTF-8' standalone='no' ?><!DOCTYPE PosReq SYSTEM "PosReq.dtd"><PosReq><SPID val="1000" /><ServID val="1000101" /><Time val="20110725-093802" /><UserInfo imei="864449000587729" imsi="460001006028940" UserAgent="generic/libra_bravo" /><CellInfo mcc="460" mnc="00" lac="4586" cid="2582" rss="-65" /><WLANIdentifier val="00:15:70:9f:62:64|00:15:70:9f:72:0c|00:25:86:4a:b9:6e|00:1c:10:aa:c0:a8|00:15:70:d0:52:60|00:18:4d:39:1b:5a|00:15:70:9f:62:66|00:15:70:9f:72:0e|00:15:70:d0:52:62|00:11:b5:fd:76:d4" /><WLANMatcher val="-51|-65|-77|-83|-87|-94|-52|-64|-87|-70" /><PosLevel val="Point" /></PosReq>"""
# WPP OK, PosLevel = Area.
#req_wpp = """<?xml version='1.0' encoding='UTF-8' standalone='no' ?><!DOCTYPE PosReq SYSTEM "PosReq.dtd"><PosReq><SPID val="1000" /><ServID val="1000101" /><Time val="20110725-141421" /><UserInfo imei="012682003400042" imsi="460007316414690" UserAgent="SEMC/LT15i_1247-1052" /><CellInfo mcc="460" mnc="00" lac="1015" cid="28837" rss="-63" /><WLANIdentifier val="00:21:27:61:16:36|00:23:cd:3f:2d:b6" /><WLANMatcher val="-88|-98" /><PosLevel val="Area" /></PosReq>"""
# WPP OK, PosLevel = Hybrid.
#req_wpp = """<?xml version='1.0' encoding='UTF-8' standalone='no' ?><!DOCTYPE PosReq SYSTEM "PosReq.dtd"><PosReq><SPID val="1000" /><ServID val="1000101" /><Time val="20110725-141421" /><UserInfo imei="012682003400042" imsi="460007316414690" UserAgent="SEMC/LT15i_1247-1052" /><CellInfo mcc="460" mnc="00" lac="1015" cid="28837" rss="-63" /><WLANIdentifier val="00:21:27:61:16:36|00:23:cd:3f:2d:b6" /><WLANMatcher val="-88|-98" /><PosLevel val="Hybrid" /></PosReq>"""
# WPP OK, PosLevel Null.
#req_wpp = """<?xml version="1.0"?><!DOCTYPE PosReq_FC SYSTEM "PosReq_FC.dtd"><PosReq_FC><SPID val="123" /><ServID val="456" /><Time val="20110130-114424" /><UserInfo imei="355302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" /><CellInfo mcc="460" mnc="00" lac="4577777" cid="3088" rss="-63" /><WLANIdentifier val="00:15:70:9f:62:64|00:25:86:4a:b9:6e|00:15:70:9f:72:0c|00:15:70:d0:52:60|00:23:cd:68:f6:d6|00:1b:11:a4:2d:c6|00:15:70:a6:a3:30|00:15:70:9f:62:66|00:15:70:9f:72:0e|00:15:70:d0:52:62|00:25:86:51:bd:54|00:15:70:a6:a3:32|00:1c:10:aa:c0:a8|00:11:b5:fd:76:d4" /><WLANMatcher val="-40|-61|-70|-72|-75|-85|-85|-40|-69|-72|-82|-84|-88|-59" /></PosReq_FC>"""
#--------------------------fpp reqs--------------------------
# Cell location OK.
#req_fpp = """<?xml version="1.0"?><!DOCTYPE PosReq_FC SYSTEM "PosReq_FC.dtd"><PosReq_FC><SPID val="123" /><ServID val="456" /><Time val="20110130-114424" /><UserInfo imei="355302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" /><CellInfo mcc="460" mnc="00" lac="4577" cid="3088" rss="-63" /></PosReq_FC>"""
# Cell location FAILED.
#req_fpp = """<?xml version='1.0' encoding='UTF-8' standalone='no' ?> <!DOCTYPE PosReq_FC SYSTEM "PosReq_FC.dtd"> <PosReq_FC> <SPID val="123" /> <ServID val="456" /> <Time val="20101228-092633" /> <UserInfo imei="351553040596788" imsi="460000894118015" UserAgent="Motorola/beihaitd" /> <CellInfo mcc="460" mnc="00" lac="4586" cid="2582" rss="-55" /> </PosReq_FC>"""
# Cell + WLAN, ONLY Cell OK.
#req_fpp = """<?xml version="1.0"?><!DOCTYPE PosReq_FC SYSTEM "PosReq_FC.dtd"><PosReq_FC><SPID val="123" /><ServID val="456" /><Time val="20110130-114424" /><UserInfo imei="355302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" /><CellInfo mcc="460" mnc="00" lac="4577" cid="3088" rss="-63" /><WLANIdentifier val="00:15:70:9f:62:6a" /><WLANMatcher val="-40" /></PosReq_FC>"""
# Illegal msg content, e.g. imei.
req_fpp = """<?xml version="1.0"?><!DOCTYPE PosReq_FC SYSTEM "PosReq_FC.dtd"><PosReq_FC><SPID val="123" /><ServID val="456" /><Time val="20110130-114424" /><UserInfo imei="AB5302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" /><CellInfo mcc="460" mnc="00" lac="4577" cid="3088" rss="-63" /><WLANIdentifier val="00:15:70:9f:62:6a" /><WLANMatcher val="-40" /></PosReq_FC>"""
# Cell + WLAN, Both OK, WLAN Better.
#req_fpp = """<?xml version="1.0"?><!DOCTYPE PosReq_FC SYSTEM "PosReq_FC.dtd"><PosReq_FC><SPID val="123" /><ServID val="456" /><Time val="20110130-114424" /><UserInfo imei="355302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" /><CellInfo mcc="460" mnc="00" lac="4577" cid="3088" rss="-63" /><WLANIdentifier val="00:15:70:9f:62:64|00:25:86:4a:b9:6e|00:15:70:9f:72:0c|00:15:70:d0:52:60|00:23:cd:68:f6:d6|00:1b:11:a4:2d:c6|00:15:70:a6:a3:30|00:15:70:9f:62:66|00:15:70:9f:72:0e|00:15:70:d0:52:62|00:25:86:51:bd:54|00:15:70:a6:a3:32|00:1c:10:aa:c0:a8|00:11:b5:fd:76:d4" /><WLANMatcher val="-40|-61|-70|-72|-75|-85|-85|-40|-69|-72|-82|-84|-88|-59" /></PosReq_FC>"""
# Cell + WLAN, ONLY WLAN OK.
#req_fpp = """<?xml version="1.0"?><!DOCTYPE PosReq_FC SYSTEM "PosReq_FC.dtd"><PosReq_FC><SPID val="123" /><ServID val="456" /><Time val="20110130-114424" /><UserInfo imei="355302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" /><CellInfo mcc="460" mnc="00" lac="4577777" cid="3088" rss="-63" /><WLANIdentifier val="00:15:70:9f:62:64|00:25:86:4a:b9:6e|00:15:70:9f:72:0c|00:15:70:d0:52:60|00:23:cd:68:f6:d6|00:1b:11:a4:2d:c6|00:15:70:a6:a3:30|00:15:70:9f:62:66|00:15:70:9f:72:0e|00:15:70:d0:52:62|00:25:86:51:bd:54|00:15:70:a6:a3:32|00:1c:10:aa:c0:a8|00:11:b5:fd:76:d4" /><WLANMatcher val="-40|-61|-70|-72|-75|-85|-85|-40|-69|-72|-82|-84|-88|-59" /></PosReq_FC>"""
#--------------------------fpp uprecs reqs--------------------------
# Cell + WLAN uploading, OK.
req_uprecs = """<?xml version="1.0"?><!DOCTYPE UpRecs SYSTEM "UpRecs.dtd"><UpRecs><SPID val="123" /><ServID val="456" /><RecNum val="2"/><UpRec><Time val="20110130-114424" /><UserInfo imei="355302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" /><CellInfo mcc="460" mnc="00" lac="4577" cid="3088" rss="-63" /><LocInfo lat="39.11343" lon="116.23366" h="35" /><WLANIdentifier val="00:15:70:9f:62:64" /><WLANMatcher val="-40" /></UpRec><UpRec><Time val="20110130-114428" /><UserInfo imei="355302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" /><CellInfo mcc="460" mnc="00" lac="4577" cid="3088" rss="-53" /><LocInfo lat="39.11342" lon="116.23346" h="34" /><WLANIdentifier val="00:15:70:9f:62:64" /><WLANMatcher val="-44" /></UpRec></UpRecs>"""
# Cell + WLAN uploading, SPID FAIL.
#req_uprecs = """<?xml version="1.0"?><!DOCTYPE UpRecs SYSTEM "UpRecs.dtd"><UpRecs><SPID val="yxtabc" /><ServID val="456" /><RecNum val="2"/><UpRec><Time val="20110130-114424" /><UserInfo imei="355302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" /><CellInfo mcc="460" mnc="00" lac="4577" cid="3088" rss="-63" /><LocInfo lat="39.11343" lon="116.23366" h="35" /><WLANIdentifier val="00:15:70:9f:62:64" /><WLANMatcher val="-40" /></UpRec><UpRec><Time val="20110130-114428" /><UserInfo imei="355302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" /><CellInfo mcc="460" mnc="00" lac="4577" cid="3088" rss="-53" /><LocInfo lat="39.11342" lon="116.23346" h="34" /><WLANIdentifier val="00:15:70:9f:62:64" /><WLANMatcher val="-44" /></UpRec></UpRecs>"""
# Cell + WLAN uploading, ServID FAIL.
#req_uprecs = """<?xml version="1.0"?><!DOCTYPE UpRecs SYSTEM "UpRecs.dtd"><UpRecs><SPID val="123" /><ServID val="yxtabc" /><RecNum val="2"/><UpRec><Time val="20110130-114424" /><UserInfo imei="355302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" /><CellInfo mcc="460" mnc="00" lac="4577" cid="3088" rss="-63" /><LocInfo lat="39.11343" lon="116.23366" h="35" /><WLANIdentifier val="00:15:70:9f:62:64" /><WLANMatcher val="-40" /></UpRec><UpRec><Time val="20110130-114428" /><UserInfo imei="355302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" /><CellInfo mcc="460" mnc="00" lac="4577" cid="3088" rss="-53" /><LocInfo lat="39.11342" lon="116.23346" h="34" /><WLANIdentifier val="00:15:70:9f:62:64" /><WLANMatcher val="-44" /></UpRec></UpRecs>"""
resp_xml = """<?xml version ="1.0"?><!DOCTYPE PosRes SYSTEM "PosRes.dtd"><PosRes><Result ErrCode="100" ErrDesc="OK"/><Coord lat="39.894943" lon="116.345218" h="42.000000"/><ErrRange val="27.84"/></PosRes>]"""

ip_vance_proxy = '192.168.109.48'
ip_vance_app1 = '192.168.109.51'
ip_vance_app2 = '192.168.109.52'
ip_vance_app3 = '192.168.109.53'
ip_wpp_cmri = '192.168.109.56'
ip_fpp_moto = '192.168.109.56' 
ip_wpp_local = 'localhost'
ip_fpp_neu = '192.168.109.58'

port_wpp_cmri = '8080'
port_wpp_vance = '8081'
port_fpp_neu = '18080'
port_fpp_moto = '18080'

urlpath_fpp_neu = 'FPP_AD/adapter'
urlpath_fpp_moto = 'fpp/servlet'
urlpath_wpp = 'wlan/distribution'

targets = {
        'wpp_py':{
                  'ip':ip_wpp_cmri, 
                'port':port_wpp_cmri, 
             'urlpath':urlpath_wpp,
            'req_data':req_wpp},
     'wpp_local':{
                  'ip':ip_wpp_local, 
                'port':port_wpp_cmri, 
             'urlpath':urlpath_wpp,
            'req_data':req_wpp},
     'wpp_vance_proxy':{
                  'ip':ip_vance_proxy, 
                'port':port_wpp_vance, 
             'urlpath':urlpath_wpp,
            'req_data':req_wpp},
     'wpp_vance_app1':{
                  'ip':ip_vance_app1, 
                'port':port_wpp_vance, 
             'urlpath':urlpath_wpp,
            'req_data':req_wpp},
     'wpp_vance_app2':{
                  'ip':ip_vance_app2, 
                'port':port_wpp_vance, 
             'urlpath':urlpath_wpp,
            'req_data':req_wpp},
     'wpp_vance_app3':{
                  'ip':ip_vance_app3, 
                'port':port_wpp_vance, 
             'urlpath':urlpath_wpp,
            'req_data':req_wpp},
       'fpp_local':{
                  'ip':ip_wpp_local, 
                'port':port_fpp_neu, 
             'urlpath':urlpath_fpp_neu,
            'req_data':req_fpp},
       'fpp_neu':{
                  'ip':ip_fpp_neu, 
                'port':port_fpp_neu, 
             'urlpath':urlpath_fpp_neu,
            'req_data':req_fpp},
      'fpp_moto':{
                  'ip':ip_fpp_moto, 
                'port':port_fpp_moto, 
             'urlpath':urlpath_fpp_moto,
            'req_data':req_fpp},
}

if __name__ == "__main__":
    ips_src = getIP()
    if 'wlan0' in ips_src: 
        ip_src = ips_src['wlan0']
    else: 
        ip_src = ips_src['eth0']

    target = targets['wpp_local']
    #target['urlpath'] = target['urlpath'].lower() # compatible with local fpp urlpath.
    # urlpath & port for nginx reverse proxy testing.
    #target['ip'] = '218.206.179.209'
    #target['port'] = '80'
    #target['req_data'] = req_uprecs
    url = 'http://%s:%s/%s' % (target['ip'], target['port'], target['urlpath'])
    print '\nRequesting %s from %s\n' % (url, ip_src)
    req_data = target['req_data']
    print req_data

    # need compression.
    #req_data = zlib.compress(req_data, zlib.Z_BEST_COMPRESSION)
    req = urllib2.Request(url=url, data=req_data)
    #req = urllib2.Request(url=url) # GET
    # need compression.
    #req.add_header("Content-Type", "application/zip")
    req.add_header("User-Agent", "WPP web service request simulator")
    resp = urllib2.urlopen(req)
    print '-'*40
    print 'Response:'
    #print resp.code
    print resp.read()
