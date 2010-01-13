#!/usr/bin/env python
from __future__ import division
import os,sys,csv,getopt,string
from time import strftime
from WLAN import scanWLAN
from GPS import getGPS
from pprint import pprint,PrettyPrinter
from config import DATPATH, RAWSUFFIX, RMPSUFFIX


def getRaw():
    """
    Collecting scanning results for WLAN & GPS.
    *return: rawdata=[ time, lat, lon, mac1|mac2, rss1|rss2 ]
    """
    #FIXME:exception handling
    if fake is True: rawdata = [ 39.9229416667, 116.472673167 ]
    else: rawdata = getGPS(); 
    timestamp = strftime('%Y%m%d-%H%M%S')
    rawdata.insert(0,timestamp)

    #FIXME:exception handling
    wlan = scanWLAN()
    #wlan = [ [ '00:0B:6B:3C:75:34','-89' ] , [ '00:25:86:23:A4:48','-86' ] ]
    #wlan = [ [] ]
    if wlan: num_fields = len(wlan[0])
    else: return rawdata

    # Raw data: time, lat, lon, mac1|mac2, rss1|rss2
    # aps: [ [mac1, mac2], [rss1, rss2] ]
    # aps_raw: [ mac1|mac2, rss1|rss2 ]
    if not num_fields == 0:
        aps = [ [ ap[i] for ap in wlan ] for i in range(num_fields) ]
        aps_raw = [ '|'.join(ap) for ap in aps ]
        rawdata.extend(aps_raw)

    return rawdata


def RadioMap(rfile):
    rawin = csv.reader( open(rfile,'r') )
    latlist=[]; lonlist=[]; mac_raw=[]; rss_raw=[]
    maclist=[]; mac_interset=[]
    for rawdata in rawin:
        spid = string.atoi(rawdata[0])
        latlist.append(string.atof(rawdata[2]))
        lonlist.append(string.atof(rawdata[3]))
        mac_raw.append(rawdata[4])
        rss_raw.append(rawdata[5])

    # mean lat/lon.
    lat_mean = sum(latlist) / len(latlist) 
    lon_mean = sum(lonlist) / len(lonlist) 

    maclist = [ macs.split('|') for macs in mac_raw ]
    rsslist = [ rsss.split('|') for rsss in rss_raw ]

    # Ugly code for packing MAC:RSS in dictionary.
    dictlist = []
    for i in range(len(maclist)):
        dict = {}
        for x in range(len(rsslist[i])):
            dict[maclist[i][x]]=rsslist[i][x]
        dictlist.append(dict)

    # Intersection of MAC address list for spid.
    inter = set( maclist.pop() )
    while not len(maclist) is 0:
        inter = inter & set(maclist.pop())
    # mac_interset: intersection of all MAC lists for spid samples.
    mac_interset = list(inter)

    # List the rss values of the MACs in intersection set.
    dictlist_intersect = {}
    for mac in mac_interset:
        dictlist_intersect[mac]=[]
        for dict in dictlist:
            dictlist_intersect[mac].append(string.atoi(dict[mac]))
    print 'lat_mean: %f\tlon_mean: %f' % ( lat_mean, lon_mean )
    #print 'dictlist_intersect: \n%s' % (dictlist_intersect)

    # Packing the MACs in intersection set and corresponding rss means to radio map.
    # RadioMap: spid, lat_mean, lon_mean, mac_interset_rmp, rss_interset_rmp
    mac_interset_rmp = '|'.join( dictlist_intersect.keys() )
    rss_interset_rmp = '|'.join([ 
        str( sum(dictlist_intersect[x])/len(dictlist_intersect[x]) )
        for x in dictlist_intersect.keys() ])
    if verbose is True:
        print 'mac_interset_rmp:rss_interset_rmp:'
        pp.pprint( [mac+' : '+rss for mac,rss in zip( 
            mac_interset_rmp.split('|'), rss_interset_rmp.split('|') )] )
    else:
        print 'mac_interset_rmp: %s\nrss_interset_rmp: %s' % \
            ( mac_interset_rmp, rss_interset_rmp )

    rmpdata = [ spid, lat_mean, lon_mean, mac_interset_rmp, rss_interset_rmp ]
    return rmpdata


def dumpCSV(csvfile, csvline):
    print 'Dumping data to %s' % csvfile
    rawout = csv.writer( open(csvfile,'a') )
    rawout.writerow(csvline)


def usage():
    print """
offline.py - Copyleft 2009-2010 Yan Xiaotian, xiaotian.yan@gmail.com.
Calibration & preprocessing for radio map generation in WLAN location fingerprinting.

usage:
    <sudo> offline <option> <infile>
option:
    -s --raw-scan=<times>:  Scan for <times> times and log in raw file. 
    -t --to-rmp=<rawfile>:  Process the given raw data to radio map. 
    -a --aio [NOT avail] :  All in one--raw scanning, followed by radio map generation.
    -i --spid=<spid>     :  Sampling point id. (default:spid+1, 'spid' in log/spid).
    -n --no-dump         :  No data dumping to file.
    -f --fake [for test] :  Fake GPS scan results in case of bad GPS reception.
    -v --verbose         :  Verbose mode.
    -h --help            :  Show this help.
"""


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 
            "s:t:ai:nfhv",
            ["raw-scan=","to-rmp=","aio","spid=","no-dump","fake","help","verbose"])
    except getopt.GetoptError:
        usage()
        sys.exit(99)

    if not opts: usage(); sys.exit(0)

    # global vars init.
    spid = 0; times = 0; tormp = False
    rawfile = None; tfail = 0
    global verbose,pp,nodump,fake
    verbose = False; pp = None; nodump = False; fake = False

    for o,a in opts:
        if o in ("-i", "--spid"):
            if a.isdigit(): spid = string.atoi(a)
            else:
                print '\nspid: %s should be a INTEGER!' % str(a)
                usage()
                sys.exit(99)
        elif o in ("-s", "--raw-scan"):
            if a.isdigit(): times = string.atoi(a)
            else: 
                print '\nError: "-s/--raw-scan" should be followed by a INTEGER!'
                usage()
                sys.exit(99)
        elif o in ("-t", "--to-rmp"):
            if not os.path.isfile(a):
                print 'Raw data file NOT exist: %s' % a
                sys.exit(99)
            else: 
                tormp = True
                rawfile = a
        elif o in ("-n", "--no-dump"):
            nodump = True
        elif o in ("-f", "--fake"):
            fake = True
        #elif o in ("-a", "--aio"):
        elif o in ("-v", "--verbose"):
            verbose = True
            pp = PrettyPrinter(indent=2)
        elif o in ("-h", "--help"):
            usage()
            sys.exit(0)
        else:
            print 'Parameter NOT supported: %s' % o
            usage()
            sys.exit(99)

    # Raw data to Radio map convertion.
    if tormp is True:
        rmpdata = []
        rmpdata = RadioMap(rawfile)
        if not rmpdata:
            print 'Error: Radio map generation FAILED: %s' % rawfile
            sys.exit(99)
        if nodump is False:
            if not rawfile == None: 
                date = strftime('%Y-%m%d')
                rmpfilename = DATPATH + date + RMPSUFFIX
                dumpCSV(rmpfilename, rmpdata)
                print '-'*65
                sys.exit(0)
            else:
                usage()
                sys.exit(99)
        else:
            spid = rmpdata[0]
            if verbose is True:
                print 'Radio Map (sampling point [%d]): ' % spid
                pp.pprint(rmpdata)
            else:
                print 'Radio Map for sampling point %d: %s' % (spid, rmpdata)
            sys.exit(0)

    # WLAN & GPS scan for raw data collection.
    if not times == 0:
        for i in range(times):
            print "Survey: %d" % (i+1)
            rawdata = getRaw()
            rawdata.insert(0, spid)

            # Rawdata Integrity check.
            # Rawdata: spid, time, lat, lon, mac1|mac2, rss1|rss2
            if len(rawdata) == 6: 
                if verbose: 
                    pp.pprint(rawdata)
                else:
                    print 'Calibrating at sampling point %d ... OK!' % spid
            else: 
                tfail += 1
                print 'Time: %s\nError: Raw integrity check failed! Next!' % rawdata[1]
                print '-'*65
                continue
            if nodump is False:
                if not os.path.isdir(DATPATH):
                    try:
                        os.umask(0) #linux system default umask: 022.
                        os.mkdir(DATPATH,0777)
                        #os.chmod(DATPATH,0777)
                    except OSError, errmsg:
                        print "Failed: %d" % str(errmsg)
                        sys.exit(99)
                date = strftime('%Y-%m%d')
                rfilename = DATPATH + date + ('-%06d' % spid) + RAWSUFFIX
                dumpCSV(rfilename, rawdata)
            print '-'*65
        
        #Scan Summary
        print '\nOK/Total:%28d/%d\n' % (times-tfail, times)


if __name__ == "__main__":
    main()
