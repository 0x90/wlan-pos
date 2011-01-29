import urllib2, urllib
#data = {'name' : 'yxt', 'password' : 'pwd'}
eg_xml = """ <entry> <host>64.172.22.154</host> </entry>"""
req_xml = """ 
<?xml version="1.0" encoding="UTF-8"?>
<PosReq>
  <SPID val="1234" />
  <ServID val="1234" />
  <Time val="20101012-160032" />
  <UserInfo imei="862030980177277" imsi="460077112409687" UserAgent="Motorola" />
  <CellInfo mcc="460" mnc="00" lac="12345" cid="12345" rss="-57" />
  <WLANIdentifier val="00:25:90:13:A4:48|00:AB:BB:3C:75:34|00:DD:01:FE:0F:20" />
  <WLANMatcher val="-88|-70|-90"/>
</PosReq>"""
resp_xml = """ 
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE PosRes SYSTEM "PosRes.dtd">
<PosRes>
        <Result ErrCode="104" ErrDesc="IntegrityFail"/>
        <Coord lat="0.000000" lon="0.000000" h="0.000000"/>
        <ErrRange val="0.00"/>
</PosRes>"""
f = urllib2.urlopen(
        url = 'http://localhost:18080/',
        data = req_xml
        #data = urllib.urlencode(data)
        )
print f.read()
