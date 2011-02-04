import urllib2, urllib
import sys
sys.path.append('/home/alexy/dev/src/wlan-pos/tool')

#data = {'name' : 'yxt', 'password' : 'pwd'}
eg_xml = """ <entry> <host>64.172.22.154</host> </entry>"""
req_xml = """ 
<?xml version='1.0' encoding='UTF-8' standalone='no' ?>
<!DOCTYPE PosReq_FC SYSTEM "PosReq_FC.dtd">
 <PosReq_FC>
  <SPID val="123" />
  <ServID val="456" />
  <Time val="20110130-114424" />
  <UserInfo imei="355302043446609" imsi="460001933113172" UserAgent="htc_asia_wwe/htc_bravo" />
  <CellInfo mcc="460" mnc="00" lac="4586" cid="2582" rss="-63" />
  <WLANIdentifier val="00:15:70:9f:62:64|00:25:86:4a:b9:6e|00:15:70:9f:72:0c|00:15:70:d0:52:60|00:23:cd:68:f6:d6|00:1b:11:a4:2d:c6|00:15:70:a6:a3:30|00:15:70:9f:62:66|00:15:70:9f:72:0e|00:15:70:d0:52:62|00:25:86:51:bd:54|00:15:70:a6:a3:32|00:1c:10:aa:c0:a8|00:11:b5:fd:76:d4" />
  <WLANMatcher val="-40|-61|-70|-72|-75|-85|-85|-40|-69|-72|-82|-84|-88|-59" />
  </PosReq_FC>"""
resp_xml = """
<?xml version ="1.0"?>
<!DOCTYPE PosRes SYSTEM "PosRes.dtd">
<PosRes>
	<Result ErrCode="100" ErrDesc="OK"/>
	<Coord lat="39.894943" lon="116.345218" h="42.000000"/>
	<ErrRange val="27.84"/>
</PosRes>]"""
# [39.895167306122453, 116.34509951020408, 24.660629537376867]

#req_xml = """ 
#<?xml version="1.0" encoding="UTF-8"?>
#<!DOCTYPE PosReq SYSTEM "PosReq.dtd">
#<PosReq_FC>
#  <SPID val="1234" />
#  <ServID val="1234" />
#  <Time val="20101012-160032" />
#  <UserInfo imei="862030980177277" imsi="460077112409687" UserAgent="Motorola" />
#  <CellInfo mcc="460" mnc="00" lac="12345" cid="12345" rss="-57" />
#  <WLANIdentifier val="00:21:91:1D:C1:06" />
#  <WLANMatcher val="-84"/>
#</PosReq_FC>"""
#resp_xml = """ 
#<?xml version="1.0" encoding="UTF-8"?>
#<!DOCTYPE PosRes SYSTEM "PosRes.dtd">
#<PosRes>
#        <Result ErrCode="104" ErrDesc="IntegrityFail"/>
#        <Coord lat="0.000000" lon="0.000000" h="0.000000"/>
#        <ErrRange val="0.00"/>
#</PosRes>"""


if __name__ == "__main__":
    from evaloc import getIPaddr
    ipaddr = getIPaddr('wlan0')['wlan0']
    port = '18080'
    path_info = 'wlan/distribution'
    url_wpp = 'http://%s:%s/%s' % (ipaddr, port, path_info)

    #req = urllib2.Request(url=url_wpp, data=urllib.urlencode(data))
    req = urllib2.Request(url=url_wpp, data=req_xml)
    resp = urllib2.urlopen(req)
    print resp.code, resp.read()
