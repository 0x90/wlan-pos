#!/usr/bin/env python
import sys,csv
infile = csv.reader( open('dat/ap.dat','r') )

kmlout = open('kml/ap.kml','w')
kmlout.write('<?xml version="1.0" encoding="UTF-8"?>\n')
kmlout.write('<kml xmlns="http://earth.google.com/kml/2.0">\n')
kmlout.write('<Folder>\n')
kmlout.write('<name>Offline Calibration</name>\n')
kmlout.write('<visibility>1</visibility>\n')

for line in infile:
    print line
    mac = line[0]
    rss = line[1]
    noise = line[2]
    wep = line[3]
    name = line[4]
    lat = line[5]
    lon = line[6]
    print "%s (%s): %s %s" % (name,mac,lat,lon)
    kmlout.write('\n')
    kmlout.write(' <Placemark>\n')
    kmlout.write(' <name>%s</name>\n' % name)
    #kmlout.write('  <description><![CDATA[ MAC:%s ]]></description>\n' % mac)
    kmlout.write('  <description>%s  %s  %s</description>\n' % (name,mac,rss))
    kmlout.write(' <View>\n')
    kmlout.write('  <longitude>%s</longitude>\n' % lon)
    kmlout.write('  <latitude>%s</latitude>\n' % lat)
    kmlout.write(' </View>\n')
    kmlout.write(' <visibility>1</visibility>\n')
    kmlout.write(' <styleUrl>root://styleMaps#default?iconId=0x307</styleUrl>\n')
    if wep =='on':
        #kmlout.write(' <Style><icon>file:///home/alexy/wlan-pos/fig/wepon.png</icon></Style>\n')
        kmlout.write(' <Style><icon>http://www.brest-wireless.net/gmap/node_interest.png</icon></Style>\n')
    else:
        kmlout.write(' <Style><icon>file:///home/alexy/wlan-pos/fig/wepoff.png</icon></Style>\n')
    kmlout.write(' <Point><coordinates>%s,%s,45</coordinates></Point>\n' % (lon,lat) )
    kmlout.write(' </Placemark>\n')

kmlout.write('</Folder>\n')
kmlout.write('</kml>')
kmlout.close()
#infile.close()
sys.exit(0)

try:
    from elementtree import ElementTree
except:
    from xml.etree import ElementTree

try:
   file = sys.argv[1]
   data = open(file,'r').read()
except:
   print sys.argv[0] + " {kismet logfile}"
   sys.exit(1)


detection = ElementTree.XML(data)

# KML Header
print """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://earth.google.com/kml/2.0">
<Document>
   <name>Kismet Log </name>
      <Folder>
         <name> Kismet Log Points </name>""" 

for node in detection.getchildren():
   try:
      ssid = node.find('SSID').text
   except AttributeError:
      #hidden SSID
      ssid = "{unknown SSID}"

   bssid = node.find('BSSID').text
   ssid = ssid.replace('&','')
   channel = node.find('channel').text
   maxrate = node.find('maxrate').text 
   encryption = node.find('encryption').text

   gps = node.find('gps-info')
   lon = gps.find('max-lon').text
   lat = gps.find('max-lat').text

   print """
    <Placemark>
      <description><![CDATA[
            <p style="font-size:8pt;font-family:monospace;">(%s , %s)</p>
           <ul>
            <li> BSSID : %s </li>
            <li> Channel : %s </li>
            <li> Max Rate : %s </li>
            <li> Encrypt : %s </li>   
            </ul>
           ]]>
          </description>
      <name>%s</name>
      <Point>
        <extrude>1</extrude>
        <altitudeMode>relativeToGround</altitudeMode>
        <coordinates>%s,%s,0</coordinates>
      </Point>
    </Placemark> """ % \
   (lon,lat,bssid,channel,maxrate,encryption,ssid,lon,lat)


# KML Footer
print """  </Folder>
 </Document>
</kml>"""
