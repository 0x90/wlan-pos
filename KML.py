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
    from pprint import pprint,PrettyPrinter
    import numpy as np
    import time

    pp = PrettyPrinter(indent=2)
    #homedir = os.path.expanduser('~')
    for type in icon_types:
        icon_types[type][1] = os.getcwd() + icon_types[type][1]

    try:
       filename = sys.argv[1]
       rawdat = csv.reader( open(filename,'r') )
    except:
       print sys.argv[0] + " <input csv file>([[mac,rss,noise,encrypt,desc,lat,lon]])"
       sys.exit(1)

    rawdat = np.array(rawdat)
    #coords = np.array(rawdat)[:,11:13].astype(float)
    pp.pprint(rawdat)

    cidrecs = {}

    for rec in rawdat:
        cid = rec[9]
        if not cid in cidrecs:
            cidrecs[cid] = [ rec ]
        else:
            cidrecs[cid].append(rec)
    #pp.pprint(cidrecs)
    print len(cidrecs)
    #sys.exit(0)

    timestamp = time.strftime('%Y%m%d-%H%M%S')
    kmlpath = 'kml/cids-%s' % timestamp
    if not os.path.isdir(kmlpath):
        try:
            os.umask(0) #linux system default umask: 022.
            os.mkdir(kmlpath,0777)
            #os.chmod(DATPATH,0777)
        except OSError, errmsg:
            print "Failed: %d" % str(errmsg)
            sys.exit(99)
    for cid in cidrecs:
        cidat = cidrecs[cid]
        indat =  [ [[rec[11], rec[12], '', 
            'UA:%s, <br> time: %s, <br> cid|rss: %s|%s, <br> mac/ss: %s/%s' %\
            (rec[5],rec[2],rec[9],rec[10],rec[14],rec[15])]] for rec in cidat ]
        pp.pprint(indat)

        kmlfile = '%s/cid-%s.kml' % (kmlpath, cid)
        genKML(data=indat, kmlfile=kmlfile, icons=icon_types)
