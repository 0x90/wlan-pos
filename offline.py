#!/usr/bin/env python
#coding=utf-8
#Parse GPS info by listening NMEA0183 GPGLL sentence from serial port.
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
    """
    #FIXME:exception handling
    rawdata = getGPS(); 
    #rawdata = [ 116.472673167, 39.9229416667 ]
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


def usage():
    print """
offline.py - Copyright 2009 Yan Xiaotian, yanxiaotian@chinamobile.com.
Calibration & preprocessing for radio map generation in WLAN location fingerprinting.

usage:
    <sudo> offline <option> <infile>
option:
    -s --raw-scan=<times>:  Scan for <times> times and log in raw file. 
    -t --to-rmp=<rawfile>:  Process the given raw data to radio map. 
    -a --aio             :  All in one--raw scanning, followed by radio map processing.
    -i --spid=<spid>     :  Sampling point id. (default:spid+1, 'spid' in log/spid).
    -v --verbose         :  Verbose mode.
    -h --help            :  Show this help.
"""


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

    #mean lat/lon.
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
    if verbose is True:
        print 'lat_mean: %f\tlon_mean: %f' % ( lat_mean, lon_mean )
        print 'dictlist_intersect: \n%s' % (dictlist_intersect)

    # Packing the MACs in intersection set and corresponding rss means to radio map.
    # RadioMap: spid, lat_mean, lon_mean, mac_interset_rmp, rss_interset_rmp
    mac_interset_rmp = '|'.join( dictlist_intersect.keys() )
    rss_interset_rmp = '|'.join([ 
        str( sum(dictlist_intersect[x])/len(dictlist_intersect[x]) )
        for x in dictlist_intersect.keys() ])
    print 'mac_interset_rmp: %s\nrss_interset_rmp: %s' % \
            ( mac_interset_rmp, rss_interset_rmp )

    rmpdata = [ spid, lat_mean, lon_mean, mac_interset_rmp, rss_interset_rmp ]
    return rmpdata


def dumpCSV(csvfile, csvline):
    print 'Dumping data to %s' % csvfile
    rawout = csv.writer( open(csvfile,'a') )
    rawout.writerow(csvline)


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 
                "s:t:ai:hv",
                ["raw-scan=", "to-rmp=", "aio", "spid=", "help", "verbose"])
    except getopt.GetoptError:
        usage()
        sys.exit(99)

    if not opts: usage()
    # global vars init.
    spid = 0; times = 0; tormp = False
    rawfile = None; scanStatus = None
    global verbose,pp 
    verbose = False; pp = None 

    for o,a in opts:
        if o in ("-i", "--spid"):
            if a.isdigit(): spid = string.atoi(a)
            else:
                #FIXME: default spid handling.
                spid = 1
        elif o in ("-s", "--raw-scan"):
            if a.isdigit(): times = string.atoi(a)
            else: times = 1
        elif o in ("-t", "--to-rmp"):
            if not os.path.isfile(a):
                print 'Raw data file NOT exist: %s' % a
                sys.exit(99)
            else: 
                tormp = True
                rawfile = a
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
        if not rawfile == None: 
            rmpdata = []
            rmpdata = RadioMap(rawfile)
            if not rmpdata:
                print 'Error: Radio map generation FAILED: %s' % rawfile
                sys.exit(99)
            date = strftime('%Y-%m%d')
            rmpfilename = DATPATH + date + RMPSUFFIX
            dumpCSV(rmpfilename, rmpdata)
            print '-'*65
            sys.exit(0)
        else:
            usage()
            sys.exit(99)

    # WLAN & GPS scan for raw data collection.
    for i in range(times):
        print "Survey: %d" % (i+1)
        rawdata = getRaw()
        rawdata.insert(0, spid)
        # Rawdata Integrity check.
        if len(rawdata) == 6: 
            scanStatus = 'Complete'
        else: scanStatus = 'Incomplete'

        if verbose: pp.pprint(rawdata)
        else: 
            print 'Calibrating at Sampling Point %d ... %s!' % (spid, scanStatus)

        # Integrity check(ignoring spid).
        # Raw data: spid, time, lat, lon, mac1|mac2, rss1|rss2
        if not len(rawdata) == 6:
            print 'Error: Integrity check Failed!'
            print '-'*65
            continue

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


if __name__ == "__main__":
    main()
