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
from config import WLAN_FAKE, LOCPATH, LOCSUFFIX, RADIUS, icon_types, props_jpg
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
    -e --eval=<loc file(s)> :  Evaluate fingerprinting quality for records in loc file,
                               including positioning count, mean error, std error.
    -f --fakewlan=<mode id> :  Fake AP scan results in case of bad WLAN coverage.
                               <mode id> same as in WLAN_FAKE of config module.
    -g --gpsfake            :  Fake coords results in case of bad GPS coverage.
    -m --map=<loc file(s)>  :  Pinpoint fix/ref point pairs in <loc file> into GMap.
    -t --test               :  Online fingerprinting test with related info logged in loc file.
    -h --help               :  Show this help.
    -v --verbose            :  Verbose mode.
example:
    #sudo python test.py -t 
    #python test.py -e /path/to/locfile 
""" % time.strftime('%Y')


def solveCDF(data=None, pickedX=None):
    """ 
    Parameters
    ----------
    data: numpy array that contains what to be solved.
    pickedX: selected X=[x1, x2, ...] that play as xtics in CDF graph.

    Returned
    ----------
    ( X(sampled sorted data), Y(probs), [ [x(.67),.67], [x(.95),.95] ] )
    """
    # CDF calculation and visualization.
    cnt_tot = len(data)
    sortData = np.array( sorted(data) )
    probs = [sortData.searchsorted(x,side='right')/cnt_tot for x in pickedX]

    feat_ratio = [.67, .95]
    feat_points = [ [ sortData[int(rat*cnt_tot)], rat ] for rat in feat_ratio ]
    pickedX.append(feat_points[0][0]); probs.append(feat_points[0][1])
    pickedX.append(feat_points[1][0]); probs.append(feat_points[1][1])

    pickedX=sorted(pickedX); probs=sorted(probs)

    return (pickedX, probs, feat_points)


def getStats(data=None):
    """ data: numpy array """
    # Total count, mean/max error, standard deviation of errors.
    cnt_tot = len(data)
    mean = data.mean()
    stdev = data.std(ddof=1)
    max = data.max()
    print '%8s  %-10s%-10s%-10s\n%s' % ('count', 'mean(m)', 'max(m)', 'stdev(m)', '-'*38)
    print '%8d  %-10.2f%-10.2f%-10.2f' % (cnt_tot, mean, max, stdev)


def plotCDF(X=None, Y=None, props=None, fPts=None, verb=0):
    """ 
    plot 2D graph with vector data 'X,Y' and properties 'props' using gnuplot.
    Note: Commented lines go with gplot mp latex term.
    """
    #TODO: support more than one cdf plot: [ [X,Y], ... ]
    if not X or not Y: print 'Invalid input data!'; sys.exit(99)
    if not props: props = props_jpg
    g = Gnuplot.Gnuplot(debug=verb)
    g('set terminal %s font %s' % (props['term'], props['font']))
    outp = 'set output "%s"' % props['outfname']; g(outp)
    ti = 'set title "%s"' % props['title']; g(ti)

    if props['size']: g('set size %s' % props['size'])
    g('set border %s' % props['border'])
    if props['grid']: g('set grid %s' % props['grid'])
    g('set key %s' % props['key'])

    g.xlabel('%s' % props['xlabel'])
    g.ylabel('%s' % props['ylabel'])
    g('set xrange [%s:%s]' % (props['xrange'][0], props['xrange'][1])) 
    g('set yrange [%s:%s]' % (props['yrange'][0], props['yrange'][1])) 
    g('set xtics %s' % props['xtics']) 
    g('set ytics %s' % props['ytics']) 

    if props['with']: utils = props['with']
    else: utils = 'lp'
    if props['legend']: leg = props['legend']
    else: leg = props['title']

    gCDF = Gnuplot.Data(X, Y, title=props['legend'], with_=utils)

    x67, y67 = fPts[0]
    x95, y95 = fPts[1]
    gPt67 = Gnuplot.Data(x67, y67, title='67\%', with_='p')
    gPt95 = Gnuplot.Data(x95, y95, title='95\%', with_='p')

    g.plot(gCDF, gPt67, gPt95)


def drawPointpairs(ptpairs):
    """ 
        Plot point pairs  into GMap.
        ptpairs: [ [fixpoint, refpoint], ... ]
    """
    icon_fix = Icon('fixloc'); icon_ref = Icon('refloc')
    cwd = os.getcwd()
    icon_fix.image  = cwd + icon_types['yellowdot'][1]
    icon_ref.image  = cwd + icon_types['reddot'][1]
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
    print 'maps: \n%s' % ('-'*35)
    for map in gmap.maps: 
        print 'id:\'%s\',\t(10 out of all)points:' % map.id
        for point in map.points[:10]: 
            print point.getAttrs()

    open('html/map.htm', 'wb').write(gmap.genHTML())


def testLoc(wlanfake=0, gpsfake=False, verbose=False):
    # Get WLAN scanning results.
    len_visAPs, wifis = getWLAN(wlanfake)

    # Fix current position.
    fixloc = fixPos(len_visAPs, wifis, verbose)
    #fixloc = [ 39.922848,116.472895 ]
    print 'fixed location: \n%s' % fixloc

    # Get GPS referenced Position.
    if not gpsfake: refloc = getGPS()
    else: refloc = [ 39.922648,116.472895 ]
    print 'referenced location: \n%s' % refloc

    # Log the fixed and referenced positioning record.
    # Logging format: [ timestamp, MAC1|MAC2..., fLat, fLon, rLat, rLon ].
    timestamp = time.strftime('%Y-%m%d-%H%M')
    visMACs = '|'.join(wifis[0])
    #error = dist_on_unitshpere(fixloc[0], fixloc[1], refloc[0], refloc[1])*RADIUS
    locline = [ timestamp, visMACs, fixloc[0], fixloc[1], refloc[0], refloc[1] ]
    print 'locline:\n%s' % locline

    date = time.strftime('%Y-%m%d')
    locfilename = LOCPATH + date + LOCSUFFIX
    dumpCSV(locfilename, locline)


def main():
    try: opts, args = getopt.getopt(sys.argv[1:], 
            "e:f:ghm:tv",
            ["eval=","fakewlan=","gpsfake","help","map=","test","verbose"])
    except getopt.GetoptError:
        print 'Error: getopt!\n'
        usage(); sys.exit(99)

    # Program terminated when NO argument followed!
    if not opts: usage(); sys.exit(0)

    verbose = False; wlanfake = 0; gpsfake = False
    eval = False; test = False; makemap = False

    for o,a in opts:
        if o in ("-e", "--eval"):
            if not os.path.isfile(a):
                print 'Loc file NOT exist: %s!' % a
                sys.exit(99)
            else: 
                eval = True
                #locfile = a
                locfiles = sys.argv[2:]
        elif o in ("-f", "--fake"):
            if a.isdigit(): 
                wlanfake = string.atoi(a)
                if wlanfake >= 0: continue
                else: pass
            else: pass
            print '\nIllegal fake WLAN scan ID: %s!' % a
            usage(); sys.exit(99)
        elif o in ("-g", "--gpsfake"):
            gpsfake = True
        elif o in ("-h", "--help"):
            usage(); sys.exit(0)
        elif o in ("-m", "--map"):
            if not os.path.isfile(a):
                print 'Loc file NOT exist: %s!' % a
                sys.exit(99)
            else: 
                makemap = True
                locfiles = sys.argv[2:]
        elif o in ("-t", "--test"):
            test = True
        elif o in ("-v", "--verbose"):
            verbose = True
            pp = PrettyPrinter(indent=2)
        else:
            print 'Parameter NOT supported: %s' % o
            usage(); sys.exit(99)

    # Check if the logging dir exists.
    if not os.path.isdir(LOCPATH):
        try: 
            os.umask(0) #linux system default umask: 022.
            os.mkdir(LOCPATH,0777)
            #os.chmod(LOCPATH,0777)
        except OSError, errmsg:
            print "Failed: %d" % str(errmsg)
            sys.exit(99)

    if test: testLoc(wlanfake, gpsfake)

    if eval:
        for locfile in locfiles:
            # Evaluate the count, mean error, std deviation for location records in locfile,
            # optionally, the fixloc and refloc point pairs can be drawn in gmap for visualization.
            if not os.path.isfile(locfile):
                print 'loc file NOT exist: %s!' % locfile
                continue

            locin = csv.reader( open(locfile, 'r') )
            pointpairs = np.array([ locline for locline in locin ])[:,2:].astype(float)
            fixcoords = pointpairs[:,:2]
            meanref = np.mean(pointpairs[:,2:], axis=0)
            errors = np.array([ dist_on_unitshpere(flat, flon, meanref[0], meanref[1])*RADIUS
                                for flat,flon in fixcoords ])

            print 'Statistics: %s' % locfile
            getStats(errors)

            x = range(0, 500, 50)
            x, y, feat_pts = solveCDF(data=errors, pickedX=x) 

            props_jpg['legend'] = locfile[locfile.rfind('/')+1:locfile.rfind('.')]
            props_jpg['outfname'] = 'cdf_' + props_jpg['legend'] + '.jpg'
            props_jpg['xrange'] = [0,500]
            props_jpg['xtics'] = 50
            plotCDF(X=x, Y=y, props=props_jpg, fPts=feat_pts, verb=0)

            # GMap html generation.
            drawPointpairs(pointpairs)


    if makemap:
        for locfile in locfiles:
            # Make GMap with fix/ref point pairs in locfile(s).
            if not os.path.isfile(locfile):
                print 'loc file NOT exist: %s!' % locfile
                continue

            locin = csv.reader( open(locfile, 'r') )
            pointpairs = np.array([ locline for locline in locin ])[:,2:-1].astype(float)
            drawPointpairs(pointpairs)


if __name__ == "__main__":
    try:
        import psyco
        psyco.bind(solveCDF)
        psyco.bind(getStats)
        psyco.bind(plotCDF)
        psyco.bind(drawPointpairs)
        psyco.bind(testLoc)
        #psyco.full()
        #psyco.log()
        #psyco.profile(0.3)
    except ImportError:
        pass

    main()
