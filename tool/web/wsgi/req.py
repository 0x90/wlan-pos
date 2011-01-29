import urllib2, urllib
#data = {'name' : 'yxt', 'password' : 'pwd'}
data = """ <entry> <host>64.172.22.154</host> </entry>"""
#data = """
#<?xml version="1.0" encoding="utf-8"?>
#<entry>
#    <host>64.172.22.154</host>
#</entry>"""
f = urllib2.urlopen(
        url = 'http://localhost:18080/',
        data = data
        #data = urllib.urlencode(data)
        )
print f.read()
