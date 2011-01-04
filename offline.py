#!/usr/bin/env python
from __future__ import division
import os
import sys
import csv
import getopt
import string
from time import strftime

import numpy as np
from pprint import pprint,PrettyPrinter

from wlan import scanWLAN_RE
from gps import getGPS
from config import DATPATH, RAWSUFFIX, RMPSUFFIX, CLUSTERKEYSIZE, icon_types, \
        db_config_my, tbl_names_my, tbl_forms_my, tbl_field_my, \
        tbl_names, tbl_field, tbl_forms, tbl_idx, tbl_files, \
        dsn_local_ora, dsn_vance_ora, dsn_local_pg, dbtype_ora, dbtype_pg, sqls, dbsvrs
from kml import genKML
from db import WppDB


def ClusterIncr(rmpfile):
    print 'Incr Clustering ...'
    rmpin = csv.reader( open(rmpfile,'r') )
    try:
        rawrmp = np.array([ fp for fp in rmpin ])
        num_cols = np.shape(rawrmp)[1]
    except csv.Error, e:
        sys.exit('\nERROR: %s, line %d: %s!\n' % (rmpfile, rmpin.line_num, e))
    # CSV format judgement.
    if num_cols == 14:
        idx_macs = 11; idx_rsss = 12
        idx_lat = 8; idx_lon = 9; idx_h = 10
        idx_time = 13
    elif num_cols == 16:
        idx_macs = 14; idx_rsss = 15
        idx_lat = 11; idx_lon = 12; idx_h = 13
        idx_time = 2
    else:
        sys.exit('\nERROR: Unsupported csv format!\n')
    print 'CSV format: %d fields' % num_cols
        
    # topaps: array of splited aps strings for all fingerprints.
    sys.stdout.write('\nSelecting MACs for clustering ... ')
    #print
    topaps = np.char.array(rawrmp[:,idx_macs]).split('|') 
    toprss = np.char.array(rawrmp[:,idx_rsss]).split('|')
    joinaps = []
    for i in xrange(len(topaps)):
        macs = np.array(topaps[i])
        rsss = np.array(toprss[i])
        idxs_max = np.argsort(rsss)[:CLUSTERKEYSIZE]
        topaps[i] = macs[idxs_max]
        joinaps.append('|'.join(topaps[i]))
        toprss[i] = '|'.join(rsss[idxs_max])
    rawrmp[:,idx_macs] = np.array(joinaps)
    rawrmp[:,idx_rsss] = np.array(toprss)
    print 'Done'

    # Clustering heuristics.
    sys.stdout.write('Fingerprints clustering:')
    print 
    # Support multi DB incr-clustering.
    dbips = ('local_pg', )
    for svrip in dbips:
        #tbl_names = ('tsttbl',)
        dbsvr = dbsvrs[svrip]
        #print 'Loading data to DB svr: %s' % svrip
        print '%s %s %s' % ('='*15, svrip, '='*15)
        tbl_names['wpp_clusteridaps']='wpp_clusteridaps_incr'
        tbl_names['wpp_cfps']='wpp_cfps_incr'
        wppdb = WppDB(dsn=dbsvr['dsn'], dbtype=dbsvr['dbtype'], tbl_idx=tbl_idx, sqls=sqls, 
                tbl_names=tbl_names,tbl_field=tbl_field,tbl_forms=tbl_forms)
        for idx, wlanmacs in enumerate(topaps):
            print '%s %s %s' % ('-'*15, idx+1, '-'*15)
            fps = rawrmp[idx,[idx_lat,idx_lon,idx_h,idx_rsss,idx_time]]
            #     cidcntseq: all query results from db: cid,count(cid),max(seq).
            # cidcntseq_max: query results with max count(cid).
            cidcntseq = wppdb.getCIDcntMaxSeq(macs=wlanmacs)
            found_cluster = False
            if cidcntseq:
                # find out the most queried cluster /w the same AP count:
                # cid count = max seq
                cidcntseq = np.array(cidcntseq)
                cidcnt = cidcntseq[:,1]
                #print cidcntseq
                idxs_sortdesc = np.argsort(cidcnt).tolist()
                idxs_sortdesc.reverse()
                #print idxs_sortdesc
                cnt_max = cidcnt.tolist().count(cidcnt[idxs_sortdesc[0]])
                cidcntseq_max = cidcntseq[idxs_sortdesc[:cnt_max],:]
                #print cidcntseq_max
                idx_belong = cidcntseq_max[:,1].__eq__(cidcntseq_max[:,2])
                #print idx_belong
                if sum(idx_belong):
                    cids_belong = cidcntseq_max[idx_belong,[0,2]]
                    #print cids_belong
                    cid = cids_belong[0]
                    if cids_belong[1] == len(wlanmacs):
                        found_cluster = True
            sys.stdout.write('Cluster searching ... ')
            if not found_cluster:
                print 'Failed!'
                # insert into cidaps/cfps with a new clusterid.
                cid = wppdb.addCluster(wlanmacs)
                wppdb.addFps(cid=cid, fps=[fps])
            else:
                print 'Found: (%d)' % cid
                # insert fingerprints into the same cluserid in table cfps.
                wppdb.addFps(cid=cid, fps=[fps])
            print

        print '...Done'
        wppdb.close()


def getRaw():
    """
    Collecting scanning results for WLAN & GPS.
    *return: rawdata=[ time, lat, lon, mac1|mac2, rss1|rss2 ]
    """
    #FIXME:exception handling
    if fake: rawdata = [ 39.9229416667, 116.472673167 ]
    else: rawdata = getGPS(); 
    timestamp = strftime('%Y%m%d-%H%M%S')
    rawdata.insert(0,timestamp)

    #FIXME:exception handling
    wlan = scanWLAN_RE()
    #wlan = [ [ '00:0B:6B:3C:75:34','-89' ] , [ '00:25:86:23:A4:48','-86' ] ]
    #wlan = [ [] ]
    # judging whether the number of scanned wlan APs more than 4 is for clustering.
    #if wlan and (len(wlan) >= CLUSTERKEYSIZE): num_fields = len(wlan[0])
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
    """
    Generating (unclustered) fingerprint for certain sampling point(specified by 
        raw file content) from GPS/WLAN raw scanned data.

    Parameters
    ----------
    rawfile : GPS/WLAN raw scanned data file (spid, time, lat, lon, macs, rsss).

    Returns
    -------
    fingerprint = [ spid, lat_mean, lon_mean, mac_interset_rmp, rss_interset_rmp, time ]
    """
    rawin = csv.reader( open(rawfile,'r') )
    latlist=[]; lonlist=[]; mac_raw=[]; rss_raw=[]
    maclist=[]; mac_interset=[]
    try:
        for rawdata in rawin:
            spid = string.atoi(rawdata[0])
            time = string.atoi(rawdata[1])
            latlist.append(string.atof(rawdata[2]))
            lonlist.append(string.atof(rawdata[3]))
            mac_raw.append(rawdata[4])
            rss_raw.append(rawdata[5])
    except csv.Error, e:
        sys.exit('\nERROR: %s, line %d: %s!\n' % (rawfile, rawin.line_num, e))

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
    print 'Unclustered fingerprint at sampling point [%d]: ' % spid
    if verbose:
        print 'mac_interset_rmp:rss_interset_rmp'
        pp.pprint( [mac+' : '+rss for mac,rss in zip( 
            mac_interset_rmp.split('|'), rss_interset_rmp.split('|') )] )
    else:
        print 'mac_interset_rmp: %s\nrss_interset_rmp: %s' % \
            ( mac_interset_rmp, rss_interset_rmp )

    fingerprint = [ spid, lat_mean, lon_mean, mac_interset_rmp, rss_interset_rmp, time ]
    return fingerprint


def genKMLfile(cfpsfile):
    """
    Generating KML format file with data in cfps sql table file.
    format of cfps table file:
    cluster id, spid, lat, lon, keyrsss
    """
    cfpsin = csv.reader( open(cfpsfile,'r') )
    cfps = np.array([ cluster for cluster in cfpsin ])[:,:4]
    cfps = [ [[ c[2], c[3], c[1], 'cluster:%s, spid:%s'%(c[0],c[1]) ]] for c in cfps ]
    if verbose: pp.pprint(cfps)
    else: print cfps
    kfile = 'kml/ap.kml'
    #homedir = os.path.expanduser('~')
    for type in icon_types:
        icon_types[type][1] = os.getcwd() + icon_types[type][1]
    genKML(cfps, kmlfile=kfile, icons=icon_types)


def ClusterAll(rmpfile):
    """
    Clustering the raw radio map fingerprints for fast indexing(mainly in db),
    generating following data structs: cid_aps, cfprints and crmp.

    Data structs
    ------------
    *cid_aps*: cluster id, keyap, and internal seqence NO of keyap in this cluster, 
        including cids(clusterids), keyaps(macs), seq(start from 1).
    *cfprints*: all clusterid-specified fingerprints,
        including cids(clusterids), lat, lon, h, rsss, time.
    *crmp*: transitional data struct for further processing like clustering or just logging,
        including cids(clusterids),spid,servid,time,imei,imsi,ua,mcc,mnc,lac,ci,rss,lat,lon,h,macs,rsss.

    Heuristics
    ----------
    (1)Offline clustering:
        visible APs >=4: clustering with top4;
        visible APs < 4: discarded.

    (2)Online declustering:
        visible APs >=4: declustering with top4, top3(if top4 fails);
        visible APs < 4: try top3 or 2 to see whether included in any cluster key AP set.
    """
    print 'All Clustering ...'
    # rmpin: compatible with fpp-wpp rawdata spec, which defines the sampling data format: 
    # fpp_specs(14col), fpp_rawdata_xls(16col)
    # IMEI      0, 3
    # IMSI      1, 4
    # UA        2, 5
    # MCC       3, 6
    # MNC       4, 7
    # LAC       5, 8
    # CI        6, 9
    # rss       7, 10
    # lat       8, 11
    # lon       9, 12
    # h         10, 13
    # wlanmacs  11, 14
    # wlanrsss  12, 15
    # Time      13, 2
    # 
    # spid        , 0
    # servid      , 1

    rmpin = csv.reader( open(rmpfile,'r') )
    try:
        rawrmp = np.array([ fp for fp in rmpin ])
        num_cols = np.shape(rawrmp)[1]
    except csv.Error, e:
        sys.exit('\nERROR: %s, line %d: %s!\n' % (rmpfile, rmpin.line_num, e))
    # CSV format judgement.
    if num_cols == 14:
        idx_macs = 11; idx_rsss = 12
        idx_lat = 8; idx_lon = 9; idx_h = 10
        idx_time = 13
    elif num_cols == 16:
        idx_macs = 14; idx_rsss = 15
        idx_lat = 11; idx_lon = 12; idx_h = 13
        idx_time = 2
    else:
        sys.exit('\nERROR: Unsupported csv format!\n')
    print 'CSV format: %d fields' % num_cols
        
    # topaps: array of splited aps strings for all fingerprints.
    sys.stdout.write('\nSelecting MACs for clustering ... ')
    #print
    topaps = np.char.array(rawrmp[:,idx_macs]).split('|') 
    toprss = np.char.array(rawrmp[:,idx_rsss]).split('|')
    joinaps = []
    for i in xrange(len(topaps)):
        macs = np.array(topaps[i])
        rsss = np.array(toprss[i])
        idxs_max = np.argsort(rsss)[:CLUSTERKEYSIZE]
        topaps[i] = macs[idxs_max]
        joinaps.append('|'.join(topaps[i]))
        toprss[i] = '|'.join(rsss[idxs_max])
        #print toprss[i]
    #print
    rawrmp[:,idx_macs] = np.array(joinaps)
    rawrmp[:,idx_rsss] = np.array(toprss)
    #pp.pprint(rawrmp[:,idx_macs])
    #pp.pprint(rawrmp[:,idx_rsss])
    print 'Done'

    # sets_keyaps: a list of AP sets for fingerprints clustering in raw radio map,
    # [set1(ap11,ap12,...),set2(ap21,ap22,...),...].
    # lsts_keyaps: a list of AP lists for fingerprints clustering in raw radio map,
    # [[ap11,ap12,...],[ap21,ap22,...],...].
    # idxs_keyaps: corresponding line indices of the ap set in sets_keyaps.
    # [[idx11,idx12,...],[idx21,idx22,...],...].
    sets_keyaps = []
    lsts_keyaps = []
    idxs_keyaps = []

    # Clustering heuristics.
    cnt = 0
    sys.stdout.write('Fingerprints clustering ... ')
    for idx_topaps in range(len(topaps)):
        taps = topaps[idx_topaps]
        # ignore when csv record has no wlan info.
        if (len(taps) == 1) and (not taps[0]): continue
        staps = set( taps )
        if (not len(sets_keyaps) == 0) and (staps in sets_keyaps):
            idx = sets_keyaps.index(staps)
            idxs_keyaps[idx].append(idx_topaps)
            continue
        idxs_keyaps.append([])
        sets_keyaps.append(staps)
        lsts_keyaps.append(taps)
        idxs_keyaps[cnt].append(idx_topaps)
        cnt += 1
    #print 'lsts_keyaps: %s' % lsts_keyaps
    print 'Done'

    # cids: list of clustering ids for all fingerprints, for indexing in sql db.
    # [ [1], [1], ..., [2],...,... ]
    # cidtmp1: [ [1,...], [2,...], ...].
    # cidtmp2: [ 1,..., 2,..., ...].
    sys.stdout.write('Fingerprints matrix slicing ... ')
    cidtmp1 = [ [cid+1]*len(idxs_keyaps[cid]) for cid in range(len(idxs_keyaps)) ]
    cidtmp2 = []; [ cidtmp2.extend(x) for x in cidtmp1 ]
    cids = [ [x] for x in cidtmp2 ]

    ord = []; [ ord.extend(x) for x in idxs_keyaps ]
    crmp = np.append(cids, rawrmp[ord,:], axis=1)
    print 'Done'

    sys.stdout.write('Constructing clusterid-keymacs mapping table ... ')
    # cid_aps: array that mapping clusterid and keyaps for cid_aps.tbl. [cid,aps,seq].
    cidaps_idx = [ idxs[0] for idxs in idxs_keyaps ]
    cid_aps = np.array([ [str(k+1),v] for k,v in enumerate(rawrmp[cidaps_idx, [idx_macs]]) ])
    # For optimized table structure of cidaps: cid, keyap, seq(start from 1).
    cid_aps_tmp = []
    for rec in cid_aps:
        aps = rec[1].split('|')
        for seq,ap in enumerate(aps):
            cid_aps_tmp.append([ rec[0], ap, seq+1 ])
    cid_aps = np.array(cid_aps_tmp)
    print 'Done'
    
    # re-arrange RSSs of each fingerprint according to its key MACs.
    # macsref: key AP MACs in cidaps table.
    # cr: clustered fingerprints data(in crmp) for each cluster.
    #print 'crmp: \n%s' % crmp
    sys.stdout.write('Re-arranging MAC-RSS for all fingerprints ... ')
    start = 0; end = 0
    for i,macsref in enumerate(lsts_keyaps):
        end = start + len(idxs_keyaps[i])
        #print 'start: %d, end: %d' % (start, end)
        if end > len(crmp)-1: cr = crmp[start:]
        else: cr = crmp[start:end]
        #print 'macsref: %s\ncr:%s' % (macsref,cr)
        # j,fpdata: jth fp data in ith cluster. 
        for j,fpdata in enumerate(cr):
            rssnew = []
            macold = fpdata[idx_macs+1].split('|')
            #print 'macold: %s' % macold
            rssold = fpdata[idx_rsss+1].split('|')
            rssnew = [ rssold[macold.index(mac)] for mac in macsref ]
            cr[j][idx_rsss+1] = '|'.join(rssnew) 
        if end > len(crmp)-1: crmp[start:] = cr
        else: crmp[start:end] = cr
        start = end
    print 'Done'

    # cfprints: array for cfprints.tbl, [cid,lat,lon,h,rsss,time].
    sys.stdout.write('Constructing clustered fingerprint table ... ')
    cfprints = crmp[:,[0,idx_lat+1,idx_lon+1,idx_h+1,idx_rsss+1,idx_time+1]]
    print 'Done'

    if verbose:
        print 'topaps:'; pp.pprint(topaps)
        print 'sets_keyaps:'; pp.pprint(sets_keyaps)
        print 'idxs_keyaps:'; pp.pprint(idxs_keyaps)
        print 'clusterids:'; pp.pprint(cids)
        print 'crmp:'; pp.pprint(crmp)
        print 'cid_aps:'; pp.pprint(cid_aps)
        print 'cfprints:'; pp.pprint(cfprints)
    #else:
    #    print 'crmp: \n%s' % crmp

    print 'Dumping DB tables:'
    crmpfilename = rmpfile.split('.')
    crmpfilename[1] = 'crmp'
    crmpfilename = '.'.join(crmpfilename)

    #timestamp = strftime('-%m%d-%H%M')
    cidaps_filename = 'tbl/cidaps.tbl'
    cfps_filename = 'tbl/cfprints.tbl'

    #np.savetxt(crmpfilename, crmp, fmt='%s',delimiter=',')
    #print '\nDumping clustered fingerprints to: %s ... Done' % crmpfilename

    np.savetxt(cidaps_filename, cid_aps, fmt='%s',delimiter=',')
    print 'Clusterid-keymacs mapping table to: %s ... Done' % cidaps_filename

    np.savetxt(cfps_filename, cfprints, fmt='%s',delimiter=',')
    print 'Clustered fingerprints table to: %s ... Done\n' % cfps_filename


def dumpCSV(csvfile, content):
    """
    Appendding csv-formed content line(s) into csvfile.
    """
    if not content: print 'dumpCSV: Null content!'; sys.exit(99)
    print 'Dumping data to %s' % csvfile
    csvout = csv.writer( open(csvfile,'a') )
    if not isinstance(content[0], list): content = [ content ]
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
    -d --db=<dbfiles>      :  Specify the db files to upload.
    -f --fake [for test]   :  Fake GPS scan results in case of bad GPS reception.
    -h --help              :  Show this help.
    -i --spid=<spid>       :  Sampling point id.
    -k --kml=<cfprints.tbl>:  Generate KML format from cfprints table file.
    -n --no-dump           :  No data dumping to file.
    -s --raw-scan=<times>  :  Scan for <times> times and log in raw file. 
    -t --to-rmp=<rawfile>  :  Process the given raw data to radio map. 
    -u --upload=<updbmode> :  Upload clustered fingerprint tables into database, in certain mode: 
                              1-initial import(default); 2-increamental update.
    -v --verbose           :  Verbose mode.
NOTE:
    <rawfile> needed by -t/--to-rmp option must NOT have empty line(s)!
"""


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ac:fhi:k:ns:t:u:v",
            ["aio","cluster","fake","help","spid=","kml=","no-dump",
             "raw-scan=","to-rmp=","upload","verbose"])
    except getopt.GetoptError:
        usage()
        sys.exit(99)

    if not opts: usage(); sys.exit(0)

    # global vars init.
    spid=0; times=0; tormp=False; updb=False
    rawfile=None; tfail=0; docluster=False; dokml=False
    global verbose,pp,nodump,fake,updbmode
    verbose=False; pp=None; nodump=False; fake=False; updbmode=1

    for o,a in opts:
        if o in ("-i", "--spid"):
            if a.isdigit(): spid = string.atoi(a)
            else:
                print '\nspid: %s should be an INTEGER!' % str(a)
                usage(); sys.exit(99)
        elif o in ("-s", "--raw-scan"):
            if a.isdigit(): times = string.atoi(a)
            else: 
                print '\nError: "-s/--raw-scan" should be followed by an INTEGER!'
                usage(); sys.exit(99)
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
        elif o in ("-k", "--kml"):
            if not os.path.isfile(a):
                print 'cfprints table file NOT exist: %s' % a
                sys.exit(99)
            else: 
                dokml = True
                cfpsfile = a
        elif o in ("-n", "--no-dump"):
            nodump = True
        elif o in ("-f", "--fake"):
            fake = True
        elif o in ("-u", "--upload"):
            if a.isdigit(): 
                updbmode = string.atoi(a)
                if not (1 <= updbmode <= 2):
                    print '\nError: updbmode: (%d) NOT supported yet!' % updbmode
                    usage(); sys.exit(99)
                else:
                    updb = True
            else: 
                print '\nError: "-d/--db" should be followed by an INTEGER!'
                usage(); sys.exit(99)
        #elif o in ("-a", "--aio"):
        elif o in ("-v", "--verbose"):
            verbose = True
            pp = PrettyPrinter(indent=2)
        elif o in ("-h", "--help"):
            usage(); sys.exit(0)
        else:
            print 'Parameter NOT supported: %s' % o
            usage(); sys.exit(99)

    # Raw data to fingerprint convertion.
    if tormp:
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
                usage(); sys.exit(99)
        else:
            if verbose: pp.pprint(fingerprint)
            else: print fingerprint
            sys.exit(0)

    # Uploading to database.
    #TODO: upload mode 2
    if updb:
        import MySQLdb
        try:
            conn = MySQLdb.connect(host = db_config_my['hostname'], 
                                   user = db_config_my['username'], 
                                 passwd = db_config_my['password'], 
                                     db = db_config_my['dbname'], 
                               compress = 1)
                            #cursorclass = MySQLdb.cursors.DictCursor)
        except MySQLdb.Error,e:
            print "\nCan NOT connect %s@server: %s!" % (username, hostname)
            print "Error(%d): %s" % (e.args[0], e.args[1])
            sys.exit(99)
        try:
            # Returns values identified by field name(or field order if no arg).
            cursor = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
            for table in tbl_names_my:
                print 'table: %s' % table
                cursor.execute(sqls['SQL_DROP_MY'] % table)
                cursor.execute(sqls['SQL_CREATETB_MY'] % (table, tbl_forms_my[table]))
                cursor.execute(sqls['SQL_CSVIN_MY'] % (tbl_files[table], table, tbl_field_my[table]))
            cursor.close()
        except MySQLdb.Error,e:
            print "Error(%d): %s" % (e.args[0], e.args[1])
            sys.exit(99)

        conn.commit()
        conn.close()

    # KML generation.
    if dokml:
        genKMLfile(cfpsfile)

    # Ordinary fingerprints clustering.
    if docluster:
        #ClusterAll(rmpfile)
        ClusterIncr(rmpfile)

    # WLAN & GPS scan for raw data collection.
    if not times == 0:
        for i in range(times):
            print "Survey: %d" % (i+1)
            rawdata = getRaw()
            rawdata.insert(0, spid)
            # Rawdata Integrity check,
            # Format: spid, time, lat, lon, mac1|mac2, rss1|rss2
            print rawdata
            if len(rawdata) == 6: 
                if verbose: 
                    pp.pprint(rawdata)
                else:
                    print 'Calibration at sampling point %d ... OK!' % spid
            else: 
                # wlan scanned APs less than CLUSTERKEYSIZE:4.
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
            print '-'*50
        #Scan Summary
        print '\nOK/Total:%28d/%d\n' % (times-tfail, times)


if __name__ == "__main__":
    main()
