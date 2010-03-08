#!/usr/bin/env python
from __future__ import division
import os,sys,getopt,string,errno,time
from pprint import pprint,PrettyPrinter
import numpy as np
from offline import dumpCSV
from online import fixPos, getWLAN
from GPS import getGPS
from config import WLAN_FAKE, DATPATH, LOCSUFFIX, RADIUS
from GEO import dist_on_unitshpere
from Map import GMap, Icon, Map, Point


def usage():
    import time
    print """
online.py - Copyleft 2009-%s Yan Xiaotian, xiaotian.yan@gmail.com.
Location fingerprinting using deterministic/probablistic approaches.

usage:
    offline <option> <infile>
option:
    -a --address=<key id>:  key id of address book configured in address.py.
                            <key id>: 1-cmri; 2-home(temporarily closed).
    -f --fake=<mode id>  :  Fake WLAN scan results in case of bad WLAN coverage.
                            <mode id> same as in WLAN_FAKE of config module.
    -v --verbose         :  Verbose mode.
    -h --help            :  Show this help.
example:
    #online.py -a 2 -v 
    #online.py -f 1 -v 
""" % time.strftime('%Y')


def main():
    try: opts, args = getopt.getopt(sys.argv[1:], 
            "a:f:hv",
            ["address=","fake","help","verbose"])
    except getopt.GetoptError:
        print 'Error: getopt!\n'
        usage(); sys.exit(99)

    # Program terminated when NO argument followed!
    #if not opts: usage(); sys.exit(0)

    verbose = False; wlanfake = 0

    for o,a in opts:
        if o in ("-a", "--address"):
            if a.isdigit(): 
                addrid = string.atoi(a)
                if 1 <= addrid <= 2: continue
                else: pass
            else: pass
            print '\nIllegal address id: %s!' % a
            usage(); sys.exit(99)
        elif o in ("-f", "--fake"):
            if a.isdigit(): 
                wlanfake = string.atoi(a)
                if wlanfake >= 0: continue
                else: pass
            else: pass
            print '\nIllegal fake WLAN scan ID: %s!' % a
            usage(); sys.exit(99)
        elif o in ("-h", "--help"):
            usage(); sys.exit(0)
        elif o in ("-v", "--verbose"):
            verbose = True
            pp = PrettyPrinter(indent=2)
        else:
            print 'Parameter NOT supported: %s' % o
            usage(); sys.exit(99)

    # Check if the logging dir exists.
    if not os.path.isdir(DATPATH):
        try: 
            os.umask(0) #linux system default umask: 022.
            os.mkdir(DATPATH,0777)
            #os.chmod(DATPATH,0777)
        except OSError, errmsg:
            print "Failed: %d" % str(errmsg)
            sys.exit(99)

    # Get WLAN scanning results.
    #len_visAPs, wifis = getWLAN(wlanfake)

    # Fix current position.
    #fixloc = fixPos(len_visAPs, wifis, verbose)
    fixloc = [ 39.922848,116.472895 ]
    print 'fixed location: \n%s' % fixloc

    # Get GPS referenced Position.
    #refloc = getGPS()
    refloc = [ 39.922648,116.472895 ]
    print 'referenced location: \n%s' % refloc

    # Log the fixed and referenced positioning record.
    # Logging format: [ timestamp, MAC1|MAC2..., fLat, fLon, rLat, rLon, error(meter) ].
    timestamp = time.strftime('%Y-%m%d-%H%M')
    #visMACs = '|'.join(wifis[0])
    #error = dist_on_unitshpere(fixloc[0], fixloc[1], refloc[0], refloc[1])*RADIUS
    #locline = [ timestamp, visMACs, fixloc[0], fixloc[1], refloc[0], refloc[1], error ]
    #print 'locline:\n%s' % locline

    #date = time.strftime('%Y-%m%d')
    #locfilename = DATPATH + date + LOCSUFFIX
    #dumpCSV(locfilename, locline)

    icon_fixloc = Icon('fixloc'); icon_refloc = Icon('refloc')
    icon_fixloc.image  = "kml/icons/reddot.png"
    icon_refloc.image  = "kml/icons/yellowdot.png"
    icon_fixloc.shadow = icon_refloc.shadow = "kml/icons/dotshadow.png"

    pFixloc = Point(loc=fixloc, txt='alg: ' + '<br>' + str(fixloc), iconid='fixloc')     
    pRefloc = Point(loc=refloc, txt='gps: ' + '<br>' + str(refloc), iconid='refloc')     

    gmap = GMap(maplist=[Map(pointlist=[pFixloc, pRefloc])], iconlist=[icon_fixloc, icon_refloc])
    gmap.maps[0].width  = "1260px"; gmap.maps[0].height = "860px"
    gmap.maps[0].zoom   = 17

    print '\nicon types: (img: null when default)\n%s' % ('-'*35)
    for icon in gmap.icons: print 'id:\'%-5s\' img:\'%s\'' % (icon.id, icon.image)
    print '\nmaps: \n%s' % ('-'*35)
    for map in gmap.maps: 
        print 'id:\'%s\',\tpoints:' % map.id
        for point in map.points: print point.getAttrs()

    open('map.htm', 'wb').write(gmap.genHTML())   # generate test file


if __name__ == "__main__":
    try:
        import psyco
        psyco.bind(main)
        #psyco.full()
        #psyco.log()
        #psyco.profile(0.3)
    except ImportError:
        pass
    main()
