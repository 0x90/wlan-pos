#!/usr/bin/env python
import sys,csv,os

cwd = os.getcwd()
#homedir = os.path.expanduser('~')
icon_encryton = cwd + '/kml/encrypton.png'
icon_encrytoff = cwd + '/kml/encryptoff.png'
dict_encrypt_icon = { 'on': [ '"encrypton"', icon_encryton ],
                     'off': [ '"encryptoff"',icon_encrytoff] }

try:
   filename = sys.argv[1]
   infile = csv.reader( open(filename,'r') )
except:
   print sys.argv[0] + " <input csv file>(mac,rss,noise,encrypt,bssid,lat,lon)"
   sys.exit(1)

kmlout = open('kml/ap.kml','w')
# KML Header
kmlout.write('<?xml version="1.0" encoding="UTF-8"?>\n')
kmlout.write('<kml xmlns="http://earth.google.com/kml/2.0">\n')
kmlout.write('<Document>\n')
kmlout.write(' <Style id=%s> \n\
                <IconStyle>\n\
                  <Icon>\n\
                      <href>%s</href>\n\
                  </Icon>\n\
                </IconStyle>\n\
              </Style>\n\
              <Style id=%s>\n\
                <IconStyle>\n\
                  <Icon>\n\
                      <href>%s</href>\n\
                  </Icon>\n\
                </IconStyle>\n\
              </Style>\n'
              % (dict_encrypt_icon['on'][0], dict_encrypt_icon['on'][1],
                dict_encrypt_icon['off'][0], dict_encrypt_icon['off'][1]) )
kmlout.write('<name>WLAN Locationing Mapping</name>\n')
kmlout.write('<Folder>\n')
kmlout.write('<name>Offline Calibration/Online Location</name>\n')
kmlout.write('<visibility>1</visibility>\n')

for line in infile:
    print line
    mac = line[0]; rss = line[1]; noise = line[2]
    encrypt = line[3]; bssid = line[4]
    lat = line[5]; lon = line[6]
    kmlout.write('\n')
    kmlout.write(' <Placemark>\n')
    kmlout.write(' <name>%s</name>\n' % bssid)
    kmlout.write(' <description><![CDATA[\n\
                    <p style="font-size:8pt;font-family:monospace;">(%s, %s)</p>\n\
                    <ul>\n\
                    <li> BSSID: %s </li>\n\
                    <li> MACAddr: %s </li>\n\
                    <li> Encrypt: %s </li>\n\
                    </ul> ]]>\n\
                   </description>\n' 
                   % (lon,lat,bssid,mac,encrypt) )
    kmlout.write(' <View>\n\
                    <longitude>%s</longitude>\n\
                    <latitude>%s</latitude>\n\
                   </View>\n'
                     % (lon,lat) )
    #kmlout.write(' <visibility>1</visibility>\n')
    if encrypt =='on': styleurl = '#encrypton'
    else: styleurl = '#encryptoff'
    kmlout.write(' <styleUrl>%s</styleUrl>\n' % styleurl )
    kmlout.write(' <Point>\n\
                    <extrude>1</extrude>\n\
                    <altitudeMode>relativeToGround</altitudeMode>\n\
                    <coordinates>%s,%s,0</coordinates>\n\
                   </Point>\n' 
                   % (lon,lat) )
    kmlout.write(' </Placemark>\n')

# KML Footer
kmlout.write('</Folder>\n')
kmlout.write('</Document>\n')
kmlout.write('</kml>')
kmlout.close()
