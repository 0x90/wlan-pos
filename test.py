#!/usr/bin/env python
from __future__ import division
import os
import sys
import getopt
import string
import time
import csv

import numpy as np
import Gnuplot, Gnuplot.funcutils

from offline import dumpCSV
from online import fixPos, getWLAN
from GPS import getGPS
from config import WLAN_FAKE, DATPATH, LOCSUFFIX, RADIUS, icon_types
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
    -e --eval=<loc file> :  Evaluate fingerprinting quality for records in loc file,
                            including positioning count, mean error, std error.
    -f --fake=<mode id>  :  Fake WLAN scan results in case of bad WLAN coverage.
                            <mode id> same as in WLAN_FAKE of config module.
    -t --test            :  Online fingerprinting test with related info logged in loc file.
    -h --help            :  Show this help.
    -v --verbose         :  Verbose mode.
example:
    #sudo python test.py -t 
    #python test.py -e /path/to/locfile 
""" % time.strftime('%Y')


def evalLoc(locfile=None):
    """
    Evaluate the count, mean error, std deviation for location records in locfile,
    optionally, the fixloc and refloc point pairs can be drawn in gmap for visualization.
    """
    if not os.path.isfile(locfile):
        print 'loc file NOT exist: %s' % locfile
        sys.exit(99)

    locin = csv.reader( open(locfile, 'r') )
    locs = np.array([ locline for locline in locin ])[:,2:].astype(float)
    cnt_tot = len(locs)
    errors = locs[:,-1]
    mean_error = errors.mean()
    stdev = errors.std(ddof=1)
    print 'Statistics: %s' % locfile
    print '%8s  %-16s%-14s\n%s' % ('count', 'mean error(m)', 'stdev(m)', '-'*38)
    print '%8d  %-16.4f%-14.4f' % (cnt_tot, mean_error, stdev)
    #TODO: plot the above statistics info, boxplot the data, with matplotlib or gnuplot.
    sortErrs = np.array( sorted(errors) )
    pickedErrs = range(sortErrs[0], 100, 10)
    #cdf = [[err, sortErrs.searchsorted(err,side='right')/cnt_tot] for err in pickedErrs]
    cdf = [sortErrs.searchsorted(err,side='right')/cnt_tot for err in pickedErrs]

    g = Gnuplot.Gnuplot(debug=1)
    g('set terminal mp latex "Romans" 7')
    outf = 'cdf.mp'
    outp = 'set output "%s"' % outf; g(outp)

    g('set size .8, .8')
    g('set key right bottom')
    g.xlabel("error/m")
    g('set xrange [0:100]')
    g('set xtics 10'); g('set ytics')
    g('set xtics nomirror'); g('set ytics nomirror')
    g('set border 3')
    g('set grid ls 8')

    ti = 'set title "CDF"'; g(ti)
    g.ylabel("probability")
    g('set yrange [0:1]'); g('set ytics .2')
    gCDF = Gnuplot.Data(pickedErrs, cdf, title=locfile, with_='lp')
            #with_='lp lw 1.5 lc -1 lt 1 pt 4 ps 0.8')
    g.plot(gCDF)

    pointpairs = locs[:,:-1]
    drawPointpairs(pointpairs)


def drawPointpairs(ptpairs):
    """ 
        Plot point pairs  into GMap.
        ptpairs: [ [fixpoint, refpoint], ... ]
    """
    icon_fix = Icon('fixloc'); icon_ref = Icon('refloc')
    cwd = os.getcwd()
    icon_fix.image  = cwd + icon_types['reddot'][1]
    icon_ref.image  = cwd + icon_types['yellowdot'][1]
    icon_fix.shadow = icon_ref.shadow = cwd + icon_types['dotshadow'][1]

    ptlist = []
    for idx,ptpair in enumerate(ptpairs):
        fixloc = [ ptpair[0], ptpair[1] ]
        refloc = [ ptpair[2], ptpair[3] ]
        ptFix = Point(loc=fixloc, 
                      txt=str(idx)+': alg: '+'<br>'+str(fixloc), 
                      iconid='fixloc')     
        ptRef = Point(loc=refloc, 
                      txt=str(idx)+': gps: '+'<br>'+str(refloc), 
                      iconid='refloc')     
        ptlist.append(ptFix)
        ptlist.append(ptRef)

    gmap = GMap(maplist=[Map(pointlist=ptlist)], iconlist=[icon_fix, icon_ref])
    gmap.maps[0].width = "1260px"; gmap.maps[0].height = "860px"
    gmap.maps[0].zoom  = 17

    print '\nicon types: (img: null when default)\n%s' % ('-'*35)
    for icon in gmap._icons: print 'id:\'%-5s\' img:\'%s\'' % (icon.id, icon.image)
    print '\nmaps: \n%s' % ('-'*35)
    for map in gmap.maps: 
        print 'id:\'%s\',\tpoints:' % map.id
        for point in map.points: 
            print point.getAttrs()

    open('html/map.htm', 'wb').write(gmap.genHTML())


def testLoc(wlanfake=0, verbose=False):
    # Get WLAN scanning results.
    len_visAPs, wifis = getWLAN(wlanfake)

    # Fix current position.
    fixloc = fixPos(len_visAPs, wifis, verbose)
    #fixloc = [ 39.922848,116.472895 ]
    print 'fixed location: \n%s' % fixloc

    # Get GPS referenced Position.
    refloc = getGPS()
    #refloc = [ 39.922648,116.472895 ]
    print 'referenced location: \n%s' % refloc

    # Log the fixed and referenced positioning record.
    # Logging format: [ timestamp, MAC1|MAC2..., fLat, fLon, rLat, rLon, error(meter) ].
    timestamp = time.strftime('%Y-%m%d-%H%M')
    visMACs = '|'.join(wifis[0])
    error = dist_on_unitshpere(fixloc[0], fixloc[1], refloc[0], refloc[1])*RADIUS
    locline = [ timestamp, visMACs, fixloc[0], fixloc[1], refloc[0], refloc[1], error ]
    print 'locline:\n%s' % locline

    date = time.strftime('%Y-%m%d')
    locfilename = DATPATH + date + LOCSUFFIX
    dumpCSV(locfilename, locline)


def main():
    try: opts, args = getopt.getopt(sys.argv[1:], 
            "e:f:htv",
            ["eval=","fake=","help","test","verbose"])
    except getopt.GetoptError:
        print 'Error: getopt!\n'
        usage(); sys.exit(99)

    # Program terminated when NO argument followed!
    if not opts: usage(); sys.exit(0)

    verbose = False; wlanfake = 0; eval = False; test = False

    for o,a in opts:
        if o in ("-e", "--eval"):
            if not os.path.isfile(a):
                print 'Loc file NOT exist: %s!' % a
                sys.exit(99)
            else: 
                eval = True
                locfile = a
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
        elif o in ("-t", "--test"):
            test = True
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

    if test: testLoc(wlanfake)

    if eval: evalLoc(locfile)


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
