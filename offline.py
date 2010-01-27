#!/usr/bin/env python
from __future__ import division
import os,sys,csv,getopt,string
from time import strftime
import numpy as np
from WLAN import scanWLAN
from GPS import getGPS
from pprint import pprint,PrettyPrinter
from config import DATPATH, RAWSUFFIX, RMPSUFFIX, CLUSTERKEYSIZE


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
    # judging whether the number of scanned wlan APs more than 4 is for clustering.
    if wlan and (len(wlan) >= 4): num_fields = len(wlan[0])
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
    """
    Generating (unclustered) fingerprint for certain sampling point(specified by 
        raw file content) from GPS/WLAN raw scanned data.

    Parameters
    ----------
    rawfile : GPS/WLAN raw scanned data file (spid, time, lat, lon, macs, rsss).

    Returns
    -------
    fingerprint = [ spid, lat_mean, lon_mean, mac_interset_rmp, rss_interset_rmp ]
    """
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
    ary_fp = ary_fp[ :, np.argsort(ary_fp[1])[:CLUSTERKEYSIZE] ]
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
    """
    Clustering the raw radio map fingerprints for fast indexing(mainly in db),
    generating following formats: cid_aps, cfprints and crmp.

    Formats
    -------
    *cid_aps*: mapping between cluster id and corresponding keyaps.
    cids(clusterids), keyaps(macs).
    *cfprints*: all cluster id specified fingerprints.
    cids(clusterids), spid, lat, lon, rsss.
    *crmp*: medium format for further processing like clustering or just logging analysis.
    cids(clusterids), spid, lat, lon, macs, rsss.

    Heuristics
    ----------
    (1)Offline clustering:
    visible APs >=4: clustering with top4;
    visible APs < 4: discarded.

    (2)Online declustering:
    visible APs >=4: declustering with top4, top3(if top4 fails);
    visible APs < 4: if top3 or 2 included in any cluster key aps.
    """
    rmpin = csv.reader( open(rmpfile,'r') )
    rawrmp = np.array([ fp for fp in rmpin ])
    # topaps: array of splited aps strings for all fingerprints.
    topaps = np.char.array(rawrmp[:,3]).split('|')

    # sets_keyaps: a set of aps for fingerprints clustering in raw radio map,
    # [set1(ap11,ap12,...),set2(ap21,ap22,...),...].
    # idxs_keyaps: corresponding line indices of the ap set in sets_keyaps.
    # [[idx11,idx12,...],[idx21,idx22,...],...].
    sets_keyaps = []
    idxs_keyaps = []

    # Clustering heuristics.
    #TODO:take inclusion relation into consideration.
    cnt = 0
    for idx_topaps in range(len(topaps)):
        taps = set( topaps[idx_topaps] )
        if not len(sets_keyaps) == 0:
            if taps in sets_keyaps:
                idx = sets_keyaps.index(taps)
                idxs_keyaps[idx].append(idx_topaps)
                continue
        idxs_keyaps.append([])
        sets_keyaps.append(taps)
        idxs_keyaps[cnt].append(idx_topaps)
        cnt += 1

    # cids: list of clustering ids for all fingerprints, for indexing in sql db.
    # [ [1], [1], ..., [2],...,... ]
    # cidtmp1: [ [1,...], [2,...], ...].
    # cidtmp2: [ 1,..., 2,..., ...].
    cidtmp1 = [ [cid+1]*len(idxs_keyaps[cid]) for cid in range(len(idxs_keyaps)) ]
    cidtmp2 = []; [ cidtmp2.extend(x) for x in cidtmp1 ]
    cids = [ [x] for x in cidtmp2 ]

    ord = []; [ ord.extend(x) for x in idxs_keyaps ]
    crmp = np.append(cids, rawrmp[ord,:], axis=1)

    # cid_aps: array that mapping clusterid and keyaps for cid_aps.tbl. [cid,aps].
    cidaps_idx = [ idxs[0] for idxs in idxs_keyaps ]
    cid_aps = np.array([ [str(k+1),v] for k,v in enumerate( rawrmp[cidaps_idx, [3]] ) ])
    # cfprints: array for cfprints.tbl, [cid,spid,lat,lon,rsss].
    cfprints = crmp[:,[0,1,2,3,5]]
    
    if verbose is True:
        print 'topaps:'; pp.pprint(topaps)
        print 'sets_keyaps:'; pp.pprint(sets_keyaps)
        print 'idxs_keyaps:'; pp.pprint(idxs_keyaps)
        print 'clusterids:'; pp.pprint(cids)
        print 'crmp:'; pp.pprint(crmp)
        print 'cid_aps:'; pp.pprint(cid_aps)
        print 'cfprints:'; pp.pprint(cfprints)
    else:
        print 'crmp: \n%s' % crmp

    crmpfilename = rmpfile.split('.')
    crmpfilename[1] = 'crmp'
    crmpfilename = '.'.join(crmpfilename)

    timestamp = strftime('-%m%d-%H%M')
    cidaps_filename = 'tbl/cidaps' + timestamp + '.tbl'
    cfprints_filename = 'tbl/cfprints' + timestamp + '.tbl'

    # numpy.savetxt(fname, array, fmt='%.18e', delimiter=' ') 
    np.savetxt(crmpfilename, crmp, fmt='%s',delimiter=',')
    print '\nDumping clustered fingerprints to: %s ... Done' % crmpfilename

    np.savetxt(cidaps_filename, cid_aps, fmt='%s',delimiter=',')
    print '\nDumping clusterid keyaps table to: %s ... Done' % cidaps_filename

    np.savetxt(cfprints_filename, cfprints, fmt='%s',delimiter=',')
    print '\nDumping clustered fingerprints table to: %s ... Done\n' % cfprints_filename


def dumpCSV(csvfile, content):
    """
    Appendding csv-formed content line(s) into csvfile.
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
    -a --aio [NOT avail]   :  All-in-one offline processing.
    -c --cluster=<rmpfile> :  Fingerprints clustering based on max-rss-APs.
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
        Cluster(rmpfile)

    # WLAN & GPS scan for raw data collection.
    if not times == 0:
        for i in range(times):
            print "Survey: %d" % (i+1)
            rawdata = getRaw()
            rawdata.insert(0, spid)
            # Rawdata Integrity check,
            # Format: spid, time, lat, lon, mac1|mac2, rss1|rss2
            if len(rawdata) == 6: 
                if verbose is True: 
                    pp.pprint(rawdata)
                else:
                    print 'Calibration at sampling point %d ... OK!' % spid
            else: 
                # wlan scanned APs less than 4.
                tfail += 1
                print 'Time: %s\nError: Raw integrity check failed! Next!' % rawdata[1]
                print '-'*65
                continue
            # Raw data dumping to file.
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
