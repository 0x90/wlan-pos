#!/usr/bin/env python
from __future__ import division
import os,sys,csv,getopt,string
from time import strftime
import numpy as np
from WLAN import scanWLAN
from GPS import getGPS
from pprint import pprint,PrettyPrinter
from config import DATPATH, RAWSUFFIX, RMPSUFFIX, INTERSIZE


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


def Fingerprint(rawfile):
    rawin = csv.reader( open(rawfile,'r') )
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
    # dictlist: [{mac1:rss1,mac2:rss2,...},{mac3:rss3,mac4:mac4,...},...]
    dictlist = []
    for i in range(len(maclist)):
        dict = {}
        for x in range(len(rsslist[i])):
            dict[maclist[i][x]] = rsslist[i][x]
        dictlist.append(dict)

    # Intersection of MAC address list for spid.
    inter = set( maclist.pop() )
    while not len(maclist) is 0:
        inter = inter & set(maclist.pop())
    # mac_interset: intersection of all MAC lists for spid samples.
    mac_interset = list(inter)

    # List the rss values of the MACs in intersection set.
    # dictlist_inters: {mac1:[rss11,rss12,...], mac2:[rss21,rss22,...],...},
    # mac_interset=[mac1, mac2,...].
    dictlist_inters = {}
    for mac in mac_interset:
        dictlist_inters[mac] = []
        for dict in dictlist:
            dictlist_inters[mac].append(string.atoi(dict[mac]))
    print 'lat_mean: %f\tlon_mean: %f' % (lat_mean, lon_mean)
    #print 'dictlist_inters: \n%s' % (dictlist_inters)

    # Packing the MACs in intersection set and corresponding rss means to fingerprint.
    # Fingerprint: spid, lat_mean, lon_mean, mac_interset_rmp, rss_interset_rmp
    # keys: MACs list of mac_interset; mrss: mean rss list of macs in keys.
    # ary_fp: array for rss sorting of mac_interset, ary_fp[0]:macs,ary_fp[1]:rsss.
    keys = dictlist_inters.keys()
    mrss = [ sum(dictlist_inters[x])/len(dictlist_inters[x]) 
            for x in dictlist_inters.keys() ]
    ary_fp = np.array(keys + mrss).reshape(2,-1)
    # The default ascending order of argsort() seems correct for finding max-rss macs here, 
    # because the respective sorted orders for strings and numbers are opposite.
    ary_fp = ary_fp[ :, np.argsort(ary_fp[1]) ]
    mac_interset_rmp = '|'.join( list(ary_fp[0]) )
    rss_interset_rmp = '|'.join( list(ary_fp[1]) )
    if verbose is True:
        print 'mac_interset_rmp:rss_interset_rmp'
        pp.pprint( [mac+' : '+rss for mac,rss in zip( 
            mac_interset_rmp.split('|'), rss_interset_rmp.split('|') )] )
    else:
        print 'mac_interset_rmp: %s\nrss_interset_rmp: %s' % \
            ( mac_interset_rmp, rss_interset_rmp )

    fingerprint = [ spid, lat_mean, lon_mean, mac_interset_rmp, rss_interset_rmp ]
    return fingerprint


def Cluster(rmpfile):
    rmpin = csv.reader( open(rmpfile,'r') )
    lat_means=[]; lon_means=[]; mac_inter=[]; rss_inter=[]
    # group all lines in rmpfile to a list.
    for fingerp in rmpin:
        spid = string.atoi(fingerp[0])
        lat_means.append(string.atof(fingerp[1]))
        lon_means.append(string.atof(fingerp[2]))
        mac_inter.append(fingerp[3])
        rss_inter.append(fingerp[4])
    pp.pprint(lat_means)
    pp.pprint(lon_means)
    pp.pprint(mac_inter)
    pp.pprint(rss_inter)

    # dict_ckeyset: {cid:[spid]}
    #for idx in range(len(mac_inte)):


    crmpfilename = rmpfile.split('.')
    crmpfilename[1] = 'crmp'
    crmpfilename = '.'.join(crmpfilename)

    sys.exit(0)



def dumpCSV(csvfile, content):
    """
    Appendding content in form of line(s) into csvfile.
    """
    if not content:
        print 'Null: %s!' % content
        sys.exit(99)
    print 'Dumping data to %s' % csvfile
    csvout = csv.writer( open(csvfile,'a') )
    if not isinstance(content[0], list):
        content = [ content ]
    csvout.writerows(content)


def usage():
    print """
offline.py - Copyleft 2009-2010 Yan Xiaotian, xiaotian.yan@gmail.com.
Calibration & preprocessing for radio map generation in WLAN location fingerprinting.

usage:
    <sudo> offline <option> <infile>
option:
    -a --aio [NOT avail]   :  All in one--raw scanning, followed by radio map generation.
    -c --cluster=<rmpfile> :  Fingerprints classification based on max-rss-APs fingerprints clustering.
    -f --fake [for test]   :  Fake GPS scan results in case of bad GPS reception.
    -h --help              :  Show this help.
    -i --spid=<spid>       :  Sampling point id.
    -n --no-dump           :  No data dumping to file.
    -s --raw-scan=<times>  :  Scan for <times> times and log in raw file. 
    -t --to-rmp=<rawfile>  :  Process the given raw data to radio map. 
    -v --verbose           :  Verbose mode.
NOTE:
    <rawfile> needed by -t/--to-rmp option must NOT have empty line(s)!
"""


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 
            "ac:fhi:ns:t:v",
            ["aio","cluster","fake","help","spid=","no-dump","raw-scan=","to-rmp=","verbose"])
    except getopt.GetoptError:
        usage()
        sys.exit(99)

    if not opts: usage(); sys.exit(0)

    # global vars init.
    spid=0; times=0; tormp=False
    rawfile=None; tfail=0; docluster=False
    global verbose,pp,nodump,fake
    verbose=False; pp=None; nodump=False; fake=False

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
        elif o in ("-c", "--cluster"):
            if not os.path.isfile(a):
                print 'Radio map file NOT exist: %s' % a
                sys.exit(99)
            else: 
                docluster = True
                rmpfile = a
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

    # Raw data to fingerprint convertion.
    if tormp is True:
        fingerprint = []
        fingerprint = Fingerprint(rawfile)
        if not fingerprint:
            print 'Error: Fingerprint generation FAILED: %s' % rawfile
            sys.exit(99)
        if nodump is False:
            if not rawfile == None: 
                date = strftime('%Y-%m%d')
                rmpfilename = DATPATH + date + RMPSUFFIX
                dumpCSV(rmpfilename, fingerprint)
                print '-'*65
                sys.exit(0)
            else:
                usage()
                sys.exit(99)
        else:
            spid = fingerprint[0]
            print 'Fingerprint (sampling point [%d]): ' % spid
            if verbose is True: pp.pprint(fingerprint)
            else: print fingerprint
            sys.exit(0)

    # Ordinary fingerprints clustering.
    if docluster is True:
        cluster_fp = []
        cluster_fp = Cluster(rmpfile)
        if not cluster_fp:
            print 'Error: Clustering FAILED: %s' % rmpfile
            sys.exit(99)

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
