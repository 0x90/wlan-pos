#!/usr/bin/env python
from __future__ import division
import os
import sys
import csv
import getopt
import string
import StringIO as sio
import platform as pf
from time import strftime, ctime
from ftplib import FTP
from bz2 import BZ2File
from smtplib import SMTP
from email.MIMEText import MIMEText
from email.Header import Header
from email.Utils import parseaddr, formataddr

import numpy as np
from pprint import pprint,PrettyPrinter

from wlan import scanWLAN_RE
#from gps import getGPS
from config import DATPATH, RAWSUFFIX, RMPSUFFIX, CLUSTERKEYSIZE, icon_types, \
        wpp_tables, DB_OFFLINE, tbl_field, tbl_forms, tbl_idx, tbl_files, \
        dsn_local_ora, dsn_vance_ora, dsn_local_pg, dbtype_ora, dbtype_pg, sqls, dbsvrs, \
        mailcfg, errmsg, FTPCFG
        #db_config_my, wpp_tables_my, tbl_forms_my, tbl_field_my
#from kml import genKML
from db import WppDB


def usage():
    import time
    print """
offline.py - Copyleft 2009-%s Yan Xiaotian, xiaotian.yan@gmail.com.
Calibration & preprocessing for radio map generation in WLAN location fingerprinting.

usage:
    <sudo> offline <option> <infile>
option:
    -a --aio [NOT avail]   :  All-in-one offline processing.
    -c --cluster=<type id> :  Fingerprints clustering, type_id: 1-All,2-Incr.
    -d --db=<dbfiles>      :  Specify the db files to upload.
    -f --fake [for test]   :  Fake GPS scan results in case of bad GPS reception.
    -h --help              :  Show this help.
    -i --spid=<spid>       :  Sampling point id.
    -k --kml=<cfprints.tbl>:  Generate KML format from cfprints table file.
    -n --no-dump           :  No data dumping to file.
    -s --raw-scan=<times>  :  Scan for <times> times and log in raw file. 
    -t --to-rmp=<rawfile>  :  Process the given raw data to radio map. 
    -u --updatedb=<mode>   :  Update algorithm data, which is generated from rawdata from FPP's FTP.
    -v --verbose           :  Verbose mode.
NOTE:
    <rawfile> needed by -t/--to-rmp option must NOT have empty line(s)!
""" % time.strftime('%Y')


def doClusterIncr(fd_csv=None, wppdb=None):
    """
    Parameters
    ----------
    fd_csv: file descriptor of rawdata in csv format.
    wppdb: object of db.WppDB.
    
    Returns
    -------
    n_inserts: { svrip : (n_newcids, n_newfps) }, in which n_newcids,n_newfps stand for:
            n_newcids: New clusters added.
            n_newfps: New FPs added.
    """
    csvdat = csv.reader(fd_csv)
    try:
        rawrmp = np.array([ fp for fp in csvdat ])
        num_rows,num_cols = np.shape(rawrmp)
    except csv.Error, e:
        sys.exit('\nERROR: line %d: %s!\n' % (csvdat.line_num, e))
    # CSV format judgement.
    print 'Parsing FPs for Incr clustering: [%s]' % num_rows
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
    #print 'CSV format: %d fields' % num_cols
        
    # topaps: array of splited aps strings for all fingerprints.
    sys.stdout.write('Selecting MACs for clustering ... ')
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
    sys.stdout.write('Executing Incr clustering ... ')
    # Support multi DB incr-clustering.
    dbips = DB_OFFLINE
    wpp_tables['wpp_clusteridaps'] = 'wpp_clusteridaps'
    wpp_tables['wpp_cfps'] = 'wpp_cfps'
    n_inserts = { 'n_newcids':0, 'n_newfps':0 }
    for svrip in dbips:
        dbsvr = dbsvrs[svrip]
        #print '%s %s %s' % ('='*15, svrip, '='*15)
        for idx, wlanmacs in enumerate(topaps):
            #print '%s %s %s' % ('-'*17, idx+1, '-'*15)
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
                    # cids_belong: [clusterid, number of keyaps]
                    cids_belong = cidcntseq_max[idx_belong,[0,2]]
                    #print cids_belong
                    cid = cids_belong[0]
                    if cids_belong[1] == len(wlanmacs):
                        found_cluster = True
            #sys.stdout.write('Cluster searching ... ')
            if not found_cluster:
                #print 'Failed!'
                # insert into cidaps/cfps with a new clusterid.
                new_cid = wppdb.addCluster(wlanmacs)
                wppdb.addFps(cid=new_cid, fps=[fps])
                n_inserts['n_newcids'] += 1
            else:
                #print 'Found: (cid: %d)' % cid
                # insert fingerprints into the same cluserid in table cfps.
                wppdb.addFps(cid=cid, fps=[fps])
            n_inserts['n_newfps'] += 1
        print 'Done'
        return n_inserts


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


def genFPs(rawfile):
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


def doClusterAll(fd_csv=None):
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
    # csvdat: compatible with fpp-wpp rawdata spec, which defines the sampling data format: 
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

    csvdat = csv.reader( fd_csv )
    try:
        rawrmp = np.array([ fp for fp in csvdat ])
        num_rows,num_cols = np.shape(rawrmp)
    except csv.Error, e:
        sys.exit('\nERROR: line %d: %s!\n' % (csvdat.line_num, e))
    print 'All Clustering -> %s FPs' % num_rows
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
    #crmpfilename = rmpfile.split('.')
    #crmpfilename[1] = 'crmp'
    #crmpfilename = '.'.join(crmpfilename)

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


def syncFtpUprecs(ftpcfg=None, ver_wpp=None):
    """
    ftpcfg: connection string.
    ver_wpp:  current wpp version of rawdata.
    vers_fpp: fpp rawdata versions needed for wpp.
    localbzs: local path(s) of rawdata bzip2(s).
    """
    ftp = FTP()
    #ftp.set_debuglevel(1)
    try:
        print ftp.connect(host=ftpcfg['ip'],port=ftpcfg['port'],timeout=10)
    except:
        sys.exit("FTP Connection Failed: %s@%s:%s !" % (ftpcfg['user'],ftpcfg['ip'],ftpcfg['port']))
    print ftp.login(user=ftpcfg['user'],passwd=ftpcfg['passwd'])
    print ftp.cwd(ftpcfg['path'])
    files = ftp.nlst()
    # Naming rule of bzip2 file: FPP_RawData_<hostname>_<ver>.csv.bz2
    try:
        bz2s_latest = [ f for f in files if f.endswith('bz2') 
                and (f.split('_')[-1].split('.')[0]).isdigit()
                and int(f.split('_')[-1].split('.')[0])>ver_wpp ]
    except ValueError:
        sys.exit('\nERROR: Rawdata bz2 file name should be: \nFPP_RawData_<hostname>_<ver>.csv.bz2!')
    localbzs = []
    for bz2 in bz2s_latest:
        cmd = 'RETR %s' % bz2
        localbz = '%s/%s' % (ftpcfg['localdir'], bz2)
        fd_local = open(localbz, 'wb')
        ftp.retrbinary(cmd, fd_local.write)
        fd_local.close()
        localbzs.append(localbz)
    #ftp.set_debuglevel(0)
    print ftp.quit()
    vers_fpp = [ int(f.split('_')[-1].split('.')[0]) for f in bz2s_latest ]
    return (vers_fpp,localbzs)


def send_email(sender, userpwd, recipient, subject, body):
    """Send an email.
    All arguments should be Unicode strings (plain ASCII works as well).
    Only the real name part of sender and recipient addresses may contain
    non-ASCII characters.
    The email will be properly MIME encoded and delivered though SMTP to
    localhost port 25.  This is easy to change if you want something different.
    The charset of the email will be the first one out of US-ASCII, ISO-8859-1
    and UTF-8 that can represent all the characters occurring in the email.
    """
    # Header class is smart enough to try US-ASCII, then the charset we
    # provide, then fall back to UTF-8.
    header_charset = 'ISO-8859-1'
    # We must choose the body charset manually
    for body_charset in 'UTF-8', 'US-ASCII', 'ISO-8859-1':
        try:
            body.encode(body_charset)
        except UnicodeError: pass
        else: break
    # Split real name (which is optional) and email address parts
    sender_name, sender_addr = parseaddr(sender)
    recipient_name, recipient_addr = parseaddr(recipient)
    # We must always pass Unicode strings to Header, otherwise it will
    # use RFC 2047 encoding even on plain ASCII strings.
    sender_name = str(Header(unicode(sender_name), header_charset))
    recipient_name = str(Header(unicode(recipient_name), header_charset))
    # Make sure email addresses do not contain non-ASCII characters
    sender_addr = sender_addr.encode('ascii')
    recipient_addr = recipient_addr.encode('ascii')
    # Create the message ('plain' stands for Content-Type: text/plain)
    msg = MIMEText(body.encode(body_charset), 'plain', body_charset)
    msg['From'] = formataddr((sender_name, sender_addr))
    msg['To'] = formataddr((recipient_name, recipient_addr))
    msg['Subject'] = Header(unicode(subject), header_charset)
    # Send the message via SMTP to localhost:25
    smtp = SMTP("smtp.gmail.com:587")
    smtp.starttls()  
    smtp.login(userpwd[0], userpwd[1])  
    smtp.sendmail(sender, recipient, msg.as_string())
    smtp.quit()


def updateAlgoData():
    """
    Update data directly used by Algo in DB(wpp_clusterid, wpp_cfps).
    1) Retrieve latest incremental rawdata(csv) from remote FTP server(hosted by FPP).
    2) Decompress bzip2, import CSV into wpp_uprecsinfo with its ver_uprecs, Update ver_uprecs in wpp_uprecsver.
    4) Incr clustering inserted rawdata for direct algo use.
    """
    dbips = DB_OFFLINE
    for svrip in dbips:
        dbsvr = dbsvrs[svrip]
        wppdb = WppDB(dsn=dbsvr['dsn'], dbtype=dbsvr['dbtype'], tbl_idx=tbl_idx, sqls=sqls, 
                tables=wpp_tables,tbl_field=tbl_field,tbl_forms=tbl_forms)
        ver_wpp = wppdb.getRawdataVersion()
        # Sync rawdata into wpp_uprecsinfo from remote FTP server.
        print 'Probing rawdata version > [%s]' % ver_wpp
        vers_fpp,localbzs = syncFtpUprecs(FTPCFG, ver_wpp)
        if not vers_fpp: print 'Not found!'; continue
        else: print 'Found new vers: %s' % vers_fpp
        # Handle each bzip2 file.
        alerts = {'vers':[], 'details':''}
        for bzfile in localbzs:
            # Filter out the ver_uprecs info from the name of each bzip file.
            ver_bzfile = bzfile.split('_')[-1].split('.')[0]
            # Update ver_uprecs in wpp_uprecsver to ver_bzfile.
            wppdb.setRawdataVersion(ver_bzfile)
            print '%s\nUpdate ver_uprecs -> [%s]' % ('-'*40, wppdb.getRawdataVersion())
            # Decompress bzip2.
            sys.stdout.write('Decompress & append rawdata ... ')
            csvdat = csv.reader( BZ2File(bzfile) )
            try:
                indat = np.array([ line for line in csvdat ])
            except csv.Error, e:
                sys.exit('\n\nERROR: %s, line %d: %s!\n' % (bzfile, csvdat.line_num, e))
            # Append ver_uprecs info to last col.
            vers = np.array([ [ver_bzfile] for i in xrange(len(indat)) ])
            indat_withvers = np.append(indat, vers, axis=1).tolist(); print 'Done'
            # Import csv into wpp_uprecsinfo.
            try:
				sys.stdout.write('Import rawdata: ')
                wppdb.insertMany(table_name='wpp_uprecsinfo', indat=indat_withvers, verb=True)
            except Exception, e:
                _lineno = sys._getframe().f_lineno
                _file = sys._getframe().f_code.co_filename
                alerts['details'] += '\n[ver:%s][%s:%s]: %s' % \
                        (ver_bzfile, _file, _lineno, str(e).replace('\n', ' '))
                alerts['vers'].append(ver_bzfile)
                print 'ERROR: Insert Rawdata Failed!'
                continue
            # Incr clustering. 
            # file described by fd_csv contains all *location enabled* rawdata from wpp_uprecsinfo.
            strWhere = 'WHERE lat!=0 and lon!=0 and ver_uprecs=%s' % ver_bzfile
            cols_select = ','.join(wppdb.tbl_field['wpp_uprecsinfo'][:-1])
            sql = wppdb.sqls['SQL_SELECT'] % (cols_select, 'wpp_uprecsinfo %s'%strWhere)
            rdata_loc = wppdb.execute(sql)
            str_rdata_loc = '\n'.join([ ','.join([str(col) for col in fp]) for fp in rdata_loc ])
            fd_csv = sio.StringIO(str_rdata_loc)
            print 'FPs for Incr clustering selected & ready'
            n_inserts = doClusterIncr(fd_csv, wppdb)
            print 'AlgoData added: [%s] clusters, [%s] FPs' % (n_inserts['n_newcids'], n_inserts['n_newfps'])
        # Move rawdata without location to another table: wpp_uprecs_noloc.
        strWhere = 'lat=0 or lon=0'
        sql = wppdb.sqls['SQL_INSERT_SELECT'] % ('wpp_uprecs_noloc', '*', 'wpp_uprecsinfo WHERE %s'%strWhere)
        wppdb.execute(sql)
        sql = wppdb.sqls['SQL_DELETE'] % ('wpp_uprecsinfo', strWhere)
        wppdb.execute(sql)
        wppdb.close()
        print 'Move noloc rawdata -> wpp_uprecs_noloc'
        if alerts['vers']:
            # Send alert email to admin.
            _func = sys._getframe().f_code.co_name
            subject = "[!]WPP ERROR: %s->%s, ver: [%s]" % (_file, _func, ','.join(alerts['vers']))
            body = ( errmsg['db'] % ('wpp_uprecsinfo','insert',alerts['details'],pf.node(),ctime()) ).decode('utf-8')
            print subject, body
            print 'Sending alert email -> %s' % mailcfg['to']
            send_email(mailcfg['from'],mailcfg['userpwd'],mailcfg['to'],subject,body)


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ac:fhi:k:ns:t:u:v",
            ["aio","cluster","fake","help","spid=","kml=","no-dump",
             "raw-scan=","to-rmp=","updatedb","verbose"])
    except getopt.GetoptError:
        usage()
        sys.exit(99)

    if not opts: usage(); sys.exit(0)

    # global vars init.
    spid=0; times=0; tormp=False; updatedb=False
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
            if not a.isdigit(): 
                print '\ncluster type: %s should be an INTEGER!' % str(a)
                usage(); sys.exit(99)
            else:
                # 1-All; 2-Incr.
                cluster_type = string.atoi(a)
                docluster = True
                rmpfile = sys.argv[3]
                if not os.path.isfile(rmpfile):
                    print 'Raw data file NOT exist: %s!' % rmpfile
                    sys.exit(99)
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
        elif o in ("-u", "--updatedb"):
            if a.isdigit(): 
                updbmode = string.atoi(a)
                if not (1 <= updbmode <= 2):
                    print '\nError: updatedb mode: (%d) NOT supported yet!' % updbmode
                    usage(); sys.exit(99)
                else:
                    updatedb = True
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
        fingerprint = genFPs(rawfile)
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

    # Update Algorithm related data.
    if updatedb:
        updateAlgoData()
        #import MySQLdb
        #try:
        #    conn = MySQLdb.connect(host = db_config_my['hostname'], 
        #                           user = db_config_my['username'], 
        #                         passwd = db_config_my['password'], 
        #                             db = db_config_my['dbname'], 
        #                       compress = 1)
        #                    #cursorclass = MySQLdb.cursors.DictCursor)
        #except MySQLdb.Error,e:
        #    print "\nCan NOT connect %s@server: %s!" % (username, hostname)
        #    print "Error(%d): %s" % (e.args[0], e.args[1])
        #    sys.exit(99)
        #try:
        #    # Returns values identified by field name(or field order if no arg).
        #    cursor = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
        #    for table in wpp_tables_my:
        #        print 'table: %s' % table
        #        cursor.execute(sqls['SQL_DROP_MY'] % table)
        #        cursor.execute(sqls['SQL_CREATETB_MY'] % (table, tbl_forms_my[table]))
        #        cursor.execute(sqls['SQL_CSVIN_MY'] % (tbl_files[table], table, tbl_field_my[table]))
        #    cursor.close()
        #except MySQLdb.Error,e:
        #    print "Error(%d): %s" % (e.args[0], e.args[1])
        #    sys.exit(99)
        #conn.commit()
        #conn.close()

    # KML generation.
    if dokml:
        genKMLfile(cfpsfile)

    # Ordinary fingerprints clustering.
    if docluster:
        if cluster_type   == 1: 
            doClusterAll(file(rmpfile))
        elif cluster_type == 2: 
            dbips = DB_OFFLINE
            for svrip in dbips:
                dbsvr = dbsvrs[svrip]
                wppdb = WppDB(dsn=dbsvr['dsn'], dbtype=dbsvr['dbtype'], tbl_idx=tbl_idx, sqls=sqls, 
                        tables=wpp_tables,tbl_field=tbl_field,tbl_forms=tbl_forms)
                n_inserts = doClusterIncr(file(rmpfile), wppdb)
                print 'Added: [%s] clusters, [%s] FPs' % (n_inserts['n_newcids'], n_inserts['n_newfps'])
                wppdb.close()
        else: sys.exit('Unsupported cluster type code: %s!' % cluster_type)

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
