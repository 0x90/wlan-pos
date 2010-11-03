#!/usr/bin/env python
#import httplib
import urllib2 as ul
import socket as sckt
 

req_content = """{
"host": "maps.google.com",
"version":"1.1.0",
[
"mac_address":"00-21-91-1D-C0-D4",
"signal_strength": -73}
]
}"""

#headers = {"Content-type": "application/jsonrequest"}
#conn = httplib.HTTPConnection("www.google.com")
#conn.request("POST", "/loc/json", req_content, headers)
#resp = conn.getresponse()
#print resp.status, resp.reason
#
#res = resp.read()
#conn.close()
#print res
#
#loc =  eval(res)
#print loc['location']['latitude']
#print loc['location']['longitude']


req_url = "https://www.google.com/loc/json"
#proxyserver = "proxy.cmcc:8080"
proxyserver = "221.130.253.132:8080"
proxy = 'http://%s' % (proxyserver)
sckt.setdefaulttimeout(10)

opener = ul.build_opener( ul.ProxyHandler({'http':proxy}) )
ul.install_opener( opener )

resp = ul.urlopen(req_url, req_content)
ret_content = resp.read()
print ret_content
