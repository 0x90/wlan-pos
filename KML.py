#!/usr/bin/env python
import sys,csv,os


def genKML(data, kmlfile, icons):
    """
    Generating KML file with input data.

    Parameters
    ----------
    data: [ [mandatory, optional], ... ] =
           [ [[lat,lon,title,desc], [mac,rss,noise,encrypt]], ... ],
        "desc" is either description for physical address or bssid for WLAN AP.
    kmlfile: abs path & filename.
    icons: icons used for pinpointing, {'key':['"key fullname"', iconfile]}.
    """
    optional = 0

    kmlout = open(kmlfile,'w')
    # KML Header
    kmlout.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    kmlout.write('<kml xmlns="http://earth.google.com/kml/2.0">\n')
    kmlout.write('<Document>\n')
    for type in icons:
        kmlout.write(' <Style id=%s> \n\
                        <IconStyle>\n\
                          <Icon>\n\
                              <href>%s</href>\n\
                          </Icon>\n\
                        </IconStyle>\n\
                       </Style>\n'
                  % (icons[type][0], icons[type][1]) )
    kmlout.write('<name>WLAN Locationing Mapping</name>\n')
    kmlout.write('<Folder>\n')
    kmlout.write('<name>Offline Calibration/Online Location</name>\n')
    kmlout.write('<visibility>1</visibility>\n')

    for line in data:
        print line
        if len(line) == 2:
            optional = 1
            mac = line[1][0]; rss = line[1][1]; noise = line[1][2]; encrypt = line[1][3]
        title=line[0][2]; desc=line[0][3]; lat = line[0][0]; lon = line[0][1]
        kmlout.write('\n')
        kmlout.write(' <Placemark>\n')
        kmlout.write(' <name>%s</name>\n' % title)
        kmlout.write(' <description><![CDATA[\n\
                        <p style="font-size:8pt;font-family:monospace;">(%s, %s)</p>\n\
                        <ul>\n\
                        <li> %s </li>\n'
                        % (lon, lat, desc) )
        if optional == 1:
            kmlout.write('<li> %s </li>\n\
                         <li> %s </li>\n'
                         % (mac,encrypt) )
        kmlout.write('</ul> ]]>\n\
                       </description>\n')
        kmlout.write(' <View>\n\
                        <longitude>%s</longitude>\n\
                        <latitude>%s</latitude>\n\
                       </View>\n'
                         % (lon,lat) )
        if optional == 1:
            if encrypt =='on': styleurl = '#encrypton'
            elif encrypt == 'off': styleurl = '#encryptoff'
        else: styleurl = '#reddot'
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


if __name__ == "__main__":
    from config import icon_types
    from pprint import pprint
    #homedir = os.path.expanduser('~')
    for type in icon_types:
        icon_types[type][1] = os.getcwd() + icon_types[type][1]

    #try:
    #   filename = sys.argv[1]
    #   rawdat = csv.reader( open(filename,'r') )
    #except:
    #   print sys.argv[0] + " <input csv file>([[mac,rss,noise,encrypt,desc,lat,lon]])"
    #   sys.exit(1)

    rawdat=[['00:24:01:FE:0F:20','-70','-127','on', 'CMCC','39.9229416667','116.472673167'], 
            ['00:24:01:FE:0F:21','-79','-127','off','CMRI','39.9228416667','116.472573167']]

    dat = [ [[line[5], line[6], line[4], line[4]], [line[0], line[1], line[2], line[3]]] for line in rawdat ]
    kfile = 'kml/ap.kml'
    genKML(data=dat, kmlfile=kfile, icons=icon_types)
