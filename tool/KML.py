f = open('ap.kml','w')
f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
f.write('<kml xmlns="http://earth.google.com/kml/2.0">\n')
f.write('<Folder>\n')
f.write('<name>Offline Calibration</name>\n')
f.write('<visibility>1</visibility>\n')

for line in results:
    name = line[0]
    wep  = line[1]
    lat  = line[3]
    lon  = line[4]
    mac  = line[7]
    print "%s (%s): %s %s" % (name,mac,lat,lon)
    f.write('\n')
    f.write(' <Placemark>\n')
    f.write(' <name>%s</name>\n' % name)
    #f.write('  <description><![CDATA[ MAC:%s ]]></description>\n' % mac)
    f.write('  <description></description>\n')
    f.write(' <View>\n')
    f.write('  <longitude>%s</longitude>\n' % lon)
    f.write('  <latitude>%s</latitude>\n' % lat)
    f.write(' </View>\n')
    f.write(' <visibility>1</visibility>\n')
    f.write(' <styleUrl>root://styleMaps#default?iconId=0x307</styleUrl>\n')
    if wep =='WLAN-WEP':
        f.write(' <Style><icon>http://www.brest-wireless.net/gmap/node_interest.png</icon></Style>\n')
    else:
        f.write(' <Style><icon>http://www.brest-wireless.net/gmap/node_online.png</icon></Style>\n')


f.write(' <Point><coordinates>%s,%s,45</coordinates></Point>\n' % (lon,lat) )


f.write(' </Placemark>\n')

f.write('</Folder>\n')
f.write('</kml>')
f.close()
