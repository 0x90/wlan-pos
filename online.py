#!/usr/bin/env python
from __future__ import division
import sys
import getopt
#import string
import errno
from pprint import pprint,PrettyPrinter
import copy as cp

import numpy as np
#import MySQLdb

#from db import WppDB, tbl_field, tbl_forms
from wlan import scanWLAN_OS#, scanWLAN_RE
from geo import dist_km
from db import WppDB
from config import db_config_my, wpp_tables_my, sqls, dbsvrs, \
        wpp_tables, tbl_field, tbl_forms, tbl_idx, tbl_files, \
        KNN, CLUSTERKEYSIZE, WLAN_FAKE, KWIN


def usage():
    import time
    print """
online.py - Copyleft 2009-%s Yan Xiaotian, xiaotian.yan@gmail.com.
Location fingerprinting using deterministic/probablistic approaches.

usage:
    offline <option> <infile>
option:
    -a --algo=<algo id>  :  Id of different online positioning algos.
                            <algo id>: 1-old(man based); 2-new(sql based).
    -f --fake=<mode id>  :  Fake WLAN scan results in case of bad WLAN coverage.
                            <mode id> same as in WLAN_FAKE of config module.
    -v --verbose         :  Verbose mode.
    -h --help            :  Show this help.
example:
    $online.py -a 2 -v -f 25  #fake wlan verbose mode using algo with id=2.
    $online.py -f 1 -v 
""" % time.strftime('%Y')


def getWLAN(fake=0):
    """
    Returns the number and corresponding MAC/RSS info of online visible APs.
    
    Parameters
    ----------
    fake: fake WLAN scan option, int, default: 0
        Use old WLAN scanned data stored in WLAN_FAKE if valid value is taken.
    
    Returns
    -------
    (len_scanAP, scannedwlan): tuple, (int, array)
        Number and corresponding MAC/RSS info of online visible APs in tuple.
    """
    if fake == 0:   # True WLAN scan.
        #scannedwlan = scanWLAN_RE()
        scannedwlan = scanWLAN_OS()
        if scannedwlan == errno.EPERM: # fcntl.ioctl() not permitted.
            print 'For more information, please use \'-h/--help\'.'
            sys.exit(99)
    else:           # CMRI or Home.
        #addrid = fake
        try: scannedwlan = WLAN_FAKE[fake]
        except KeyError, e:
            print "\nError(%s): Illegal WLAN fake ID: '%d'!" % (e, fake) 
            print "Supported IDs: %s" % WLAN_FAKE.keys()
            sys.exit(99)
    # Address book init.
    #addr = addr_book[addrid]

    len_scanAP = len(scannedwlan)
    print 'Online visible APs: %d' % len_scanAP
    if len(scannedwlan) == 0: sys.exit(0)   

    INTERSET = min(CLUSTERKEYSIZE, len_scanAP)
    # All integers in rss field returned by scanWLAN_OS() 
    # are implicitly converted to strings during np.array(scannedwlan).
    scannedwlan = np.array(scannedwlan).T
    idxs_max = np.argsort(scannedwlan[1])[:INTERSET]
    # TBE: Necessity of different list comprehension for maxmacs and maxrsss.
    scannedwlan = scannedwlan[:,idxs_max]
    print scannedwlan

    return (INTERSET, scannedwlan)


def fixPos_old(len_wlan, wlan, verb=False):
    """
    Returns the online fixed user location in lat/lon format.
    
    Parameters
    ----------
    len_wlan: int, mandatory
        Number of online visible WLAN APs.
    wlan: np.array, string list, mandatory
        Array of MAC/RSS for online visible APs.
        e.g. [['00:15:70:9E:91:60' '00:15:70:9E:91:61' '00:15:70:9E:91:62' '00:15:70:9E:6C:6C']
              ['-55' '-56' '-57' '-68']]. 
    verb: verbose mode option, default: False
        More debugging info if enabled(True).
    
    Returns
    -------
    posfix: np.array, float
        Final fixed location(lat, lon).
        e.g. [ 39.922942  116.472673 ]
    """
    interpart_offline = False; interpart_online = False
    if verb: pp = PrettyPrinter(indent=2)


    try: conn = MySQLdb.connect(host = db_config_my['hostname'], 
                                user = db_config_my['username'], 
                              passwd = db_config_my['password'], 
                                  db = db_config_my['dbname'], 
                            compress = 1)
                         #cursorclass = MySQLdb.cursors.DictCursor)
    except MySQLdb.Error,e:
        print "Error(%d): %s" % (e.args[0], e.args[1])
        sys.exit(99)
    
    try:
        cursor = conn.cursor()
        table = wpp_tables_my['cidaps']
        #print 'select from table: %s' % table
        cursor.execute(sqls['SQL_SELECT'] % ('*', table))
        cidaps = cursor.fetchall()
    except MySQLdb.Error, e:
        print "Error(%d): %s" % (e.args[0], e.args[1])
        cursor.close(); conn.close()
        sys.exit(99)

    # cidaps: (('cid1', 'mac11|mac12|...'), ('cid2', 'mac21|mac22|...'), ...)
    #   cids: ['cid1', 'cid2', ...]
    # topaps: [['mac11', 'mac12', ...], ['mac21', 'mac22', ...], ...]
    cidaps = np.char.array(cidaps)
    cids = cidaps[:,0]; topaps = cidaps[:,1].split('|')
    set_maxmacs = set(wlan[0])

    # lst_NOInter: list of number of intersect APs between visible APs and all clusters.
    #       maxNI: the maximum element of lst_NOInter.
    # idxs_maxNOInter: list of indices of cids/topaps with largest intersect AP set.
    # keys: ID and key APs of matched cluster(s) with max intersect APs.
    lst_NOInter = np.array([ len(set_maxmacs & set(aps)) for aps in topaps ])
    idxs_sortedNOInter = np.argsort( lst_NOInter )
    maxNI = lst_NOInter[idxs_sortedNOInter[-1]]
    if maxNI == 0: # no intersection found
        print 'NO overlapping cluster found! Fingerprinting TERMINATED!'
        return []
    elif maxNI < CLUSTERKEYSIZE:
        # size of intersection set < offline key AP set size:4, 
        # offline keymacs/keyrsss (not online maxmacs/maxrsss) need to be cut down.
        interpart_offline = True
        if maxNI < len_wlan: #TODO: TBE.
            # size of intersection set < online AP set size:len_wlan < CLUSTERKEYSIZE, 
            # not only keymacs/keyrsss, but also maxmacs/maxrsss need to be cut down.
            interpart_online = True
        if verb: print 'Partly matched cluster(s) found(max intersect size: %d):' % maxNI
    else: 
        if verb: print 'Full matched cluster(s) found:' 
        else: pass
    idx_start = lst_NOInter[idxs_sortedNOInter].searchsorted(maxNI)
    idxs_maxNOInter = idxs_sortedNOInter[idx_start:]
    keys = [ [cids[idx], topaps[idx]] for idx in idxs_maxNOInter ]
    if verb: pp.pprint(keys)

    # fps_cand: [ min_spid1:[cid,spid,lat,lon,rsss], min_spid2, ... ]
    all_pos_lenrss = []
    fps_cand = []; sums_cand = []
    if verb: print '='*35
    for cid,keyaps in keys:
        try: # Returns values identified by field name(or field order if no arg).
            table = wpp_tables_my['cfps']
            state_where = 'cid = %s' % cid
            if verb: print 'select %s from table %s' % (state_where, table)
            cursor.execute(sqls['SQL_SELECT'] % ('*' , "%s where %s"%(table,state_where)))
            keycfps = cursor.fetchall()
        except MySQLdb.Error,e:
            print "Error(%d): %s" % (e.args[0], e.args[1])
            cursor.close(); conn.close()
            sys.exit(99)
        if verb:
            print ' keyaps: %s' % keyaps
            if len(keycfps) == 1: print 'keycfps: %s' % keycfps
            else: print 'keycfps: '; pp.pprint(keycfps)
        # Fast fix when the ONLY 1 selected cid has ONLY 1 fp in 'cfps'.
        if len(keys) == cursor.rowcount == 1:
            fps_cand = [ list(keycfps[0]) ]
            break
        pos_lenrss = (np.array(keycfps)[:,2:4].astype(float)).tolist()
        keyrsss = np.char.array(keycfps)[:,4].split('|') #4: column order in cfps.tbl
        keyrsss = np.array([ [float(rss) for rss in spid] for spid in keyrsss ])
        for idx,pos in enumerate(pos_lenrss):
            pos_lenrss[idx].append(len(keyrsss[idx]))
        all_pos_lenrss.extend(pos_lenrss)
        # Rearrange key MACs/RSSs in 'keyrsss' according to intersection set 'keyaps'.
        if interpart_offline and interpart_online:
            wl = cp.deepcopy(wlan) # mmacs->wl[0]; mrsss->wl[1]
            idxs_inters = [ idx for idx,mac in enumerate(wlan[0]) if mac in keyaps ]
            wl = wl[:,idxs_inters]
        else: wl = wlan
        idxs_taken = [ keyaps.index(x) for x in wl[0] ]
        keyrsss = keyrsss.take(idxs_taken, axis=1)
        mrsss = wl[1].astype(int)
        # Euclidean dist solving and sorting.
        #  fps_cand: [ min_spid1:[cid, spid, lat, lon, macs], min_spid2, ... ]
        sum_rss = np.sum( (mrsss-keyrsss)**2, axis=1 )
        fps_cand.extend( keycfps )
        sums_cand.extend( sum_rss )
        if verb:
            print 'sum_rss: %s' % sum_rss
            print '-'*35

    # Location estimation.
    if len(fps_cand) > 1:
        # KNN
        # lst_set_sums_cand: list format for set of sums_cand.
        # bound_dist: distance boundary for K-min distances.
        lst_set_sums_cand =  np.array(list(set(sums_cand)))
        idx_bound_dist = np.argsort(lst_set_sums_cand)[:KNN][-1]
        bound_dist = lst_set_sums_cand[idx_bound_dist]
        idx_sums_sort = np.argsort(sums_cand)

        sums_cand = np.array(sums_cand)
        fps_cand = np.array(fps_cand)

        sums_cand_sort = sums_cand[idx_sums_sort]
        idx_bound_fp = np.searchsorted(sums_cand_sort, bound_dist, 'right')
        idx_sums_sort_bound = idx_sums_sort[:idx_bound_fp]
        #idxs_kmin = np.argsort(min_sums)[:KNN]
        sorted_sums = sums_cand[idx_sums_sort_bound]
        sorted_fps = fps_cand[idx_sums_sort_bound]
        if verb:
            print 'k-dists: \n%s\nk-locations: \n%s' % (sorted_sums, sorted_fps)
        # DKNN
        if sorted_sums[0]: 
            boundry = sorted_sums[0]*KWIN
        else: 
            if sorted_sums[1]:
                boundry = KWIN
                # What the hell are the following two lines doing here!
                #idx_zero_bound = np.searchsorted(sorted_sums, 0, side='right')
                #sorted_sums[:idx_zero_bound] = boundry / (idx_zero_bound + .5)
            else: boundry = 0
        idx_dkmin = np.searchsorted(sorted_sums, boundry, side='right')
        dknn_sums = sorted_sums[:idx_dkmin].tolist()
        dknn_fps = sorted_fps[:idx_dkmin]
        if verb: print 'dk-dists: \n%s\ndk-locations: \n%s' % (dknn_sums, dknn_fps)
        # Weighted_AVG_DKNN.
        num_dknn_fps = len(dknn_fps)
        if  num_dknn_fps > 1:
            coors = dknn_fps[:,2:4].astype(float)
            num_keyaps = np.array([ rsss.count('|')+1 for rsss in dknn_fps[:,-1] ])
            # ww: weights of dknn weights.
            ww = np.abs(num_keyaps - len_wlan).tolist()
            #print ww
            if not np.all(ww):
                if np.any(ww):
                    ww_sort = np.sort(ww)
                    #print 'ww_sort:' , ww_sort
                    idx_dknn_sums_sort = np.searchsorted(ww_sort, 0, 'right')
                    #print 'idx_dknn_sums_sort', idx_dknn_sums_sort
                    ww_2ndbig = ww_sort[idx_dknn_sums_sort] 
                    w_zero = ww_2ndbig / (len(ww)*ww_2ndbig)
                else:
                    w_zero = 1
                for idx,sum in enumerate(ww):
                    if not sum: ww[idx] = w_zero
            #print 'ww:', ww
            ws = np.array(ww) + dknn_sums
            weights = np.reciprocal(ws)
            if verb: print 'coors: \n%s\nweights: %s' % (coors, weights)
            posfix = np.average(coors, axis=0, weights=weights)
        else: posfix = np.array(dknn_fps[0][2:4]).astype(float)
        # ErrRange Estimation (more than 1 relevant clusters).
        idxs_clusters = idx_sums_sort_bound[:idx_dkmin]
        if len(idxs_clusters) == 1: 
            if maxNI == 1: poserr = 100
            else: poserr = 50
        else: 
            if verb:
                print 'idxs_clusters: %s' % idxs_clusters
                print 'all_pos_lenrss:'; pp.pprint(all_pos_lenrss)
            #allposs_dknn = np.vstack(np.array(all_pos_lenrss, object)[idxs_clusters])
            allposs_dknn = np.array(all_pos_lenrss, object)[idxs_clusters]
            if verb: print 'allposs_dknn:'; pp.pprint(allposs_dknn)
            poserr = np.average([ dist_km(posfix[1], posfix[0], p[1], p[0])*1000 
                for p in allposs_dknn ]) 
    else:
        fps_cand = fps_cand[0][:-1]
        if verb: print 'location:\n%s' % fps_cand
        posfix = np.array(fps_cand[2:4])
        # ErrRange Estimation (only 1 relevant clusters).
        N_fp = len(keycfps)
        if N_fp == 1: 
            if maxNI == 1: poserr = 100
            else: poserr = 50
        else:
            if verb:
                print 'posfix: %s' % posfix
                print 'all_pos_lenrss: '; pp.pprint(all_pos_lenrss)
            poserr = np.sum([ dist_km(posfix[1], posfix[0], p[1], p[0])*1000 
                for p in all_pos_lenrss ]) / (N_fp-1)
    ret = posfix.tolist()
    ret.append(poserr)
    if verb: print 'posresult: %s' % ret
    # db close.
    cursor.close()
    conn.close()
    return ret


def fixPos(len_wlan, wlan, verb=False):
    """
    Returns the online fixed user location in lat/lon format.
    
    Parameters
    ----------
    len_wlan: int, mandatory
        Number of online visible WLAN APs.
    wlan: np.array, string list, mandatory
        Array of MAC/RSS for online visible APs.
        e.g. [['00:15:70:9E:91:60' '00:15:70:9E:91:61' '00:15:70:9E:91:62' '00:15:70:9E:6C:6C']
              ['-55' '-56' '-57' '-68']]. 
    verb: verbose mode option, default: False
        More debugging info if enabled(True).
    
    Returns
    -------
    posfix: np.array, float
        Final fixed location(lat, lon).
        e.g. [ 39.922942  116.472673 ]
    """
    interpart_offline = False; interpart_online = False
    if verb: pp = PrettyPrinter(indent=2)

    #dbip = '192.168.109.54'
    dbip = 'local_pg'
    dbsvr = dbsvrs[dbip]
    wppdb = WppDB(dsn=dbsvr['dsn'], dbtype=dbsvr['dbtype'], tbl_idx=tbl_idx, sqls=sqls, 
            tables=wpp_tables, tbl_field=tbl_field, tbl_forms=tbl_forms)
    # db query result: [ maxNI, keys:[ [keyaps:[], keycfps:(())], ... ] ].
    # maxNI=0 if no cluster found.
    maxNI,keys = wppdb.getBestClusters(macs=wlan[0])
    wppdb.close()
    #maxNI,keys = [2, [
    #    [['00:21:91:1D:C0:D4', '00:19:E0:E1:76:A4', '00:25:86:4D:B4:C4'], 
    #        [[5634, 5634, 39.898019, 116.367113, '-83|-85|-89']] ],
    #    [['00:21:91:1D:C0:D4', '00:25:86:4D:B4:C4'],
    #        [[6161, 6161, 39.898307, 116.367233, '-90|-90']] ] ]]
    if maxNI == 0: # no intersection found
        print 'NO cluster found! Fingerprinting TERMINATED!'
        return []
    elif maxNI < CLUSTERKEYSIZE:
        # size of intersection set < offline key AP set size:4, 
        # offline keymacs/keyrsss (not online maxmacs/maxrsss) need to be cut down.
        interpart_offline = True
        if maxNI < len_wlan: #TODO: TBE.
            # size of intersection set < online AP set size(len_wlan) < CLUSTERKEYSIZE,
            # not only keymacs/keyrsss, but also maxmacs/maxrsss need to be cut down.
            interpart_online = True
        if verb: print 'Partly[%d] matched cluster(s) found:' % maxNI
    else: 
        if verb: print 'Full matched cluster(s) found:' 
        else: pass
    if verb: pp.pprint(keys)

    # Evaluation|sort of similarity between online FP & radio map FP.
    # fps_cand: [ min_spid1:[cid,spid,lat,lon,rsss], min_spid2, ... ]
    # keys: ID and key APs of matched cluster(s) with max intersect APs.
    all_pos_lenrss = []
    fps_cand = []; sums_cand = []
    if verb: print '='*35
    for keyaps,keycfps in keys:
        if verb:
            print ' keyaps: %s' % keyaps
            if len(keycfps) == 1: print 'keycfps: %s' % keycfps
            else: print 'keycfps: '; pp.pprint(keycfps)
        # Fast fix when the ONLY 1 selected cid has ONLY 1 fp in 'cfps'.
        if len(keys)==1 and len(keycfps)==1:
            fps_cand = [ list(keycfps[0]) ]
            break
        pos_lenrss = (np.array(keycfps)[:,1:3].astype(float)).tolist()
        keyrsss = np.char.array(keycfps)[:,4].split('|') #4: column order in cfps.tbl
        keyrsss = np.array([ [float(rss) for rss in spid] for spid in keyrsss ])
        for idx,pos in enumerate(pos_lenrss):
            pos_lenrss[idx].append(len(keyrsss[idx]))
        all_pos_lenrss.extend(pos_lenrss)
        # Rearrange key MACs/RSSs in 'keyrsss' according to intersection set 'keyaps'.
        if interpart_offline:
            if interpart_online:
                wl = cp.deepcopy(wlan) # mmacs->wl[0]; mrsss->wl[1]
                idxs_inters = [ idx for idx,mac in enumerate(wlan[0]) if mac in keyaps ]
                wl = wl[:,idxs_inters]
            else: wl = wlan
        else: wl = wlan
        idxs_taken = [ keyaps.index(x) for x in wl[0] ]
        keyrsss = keyrsss.take(idxs_taken, axis=1)
        mrsss = wl[1].astype(int)
        # Euclidean dist solving and sorting.
        sum_rss = np.sum( (mrsss-keyrsss)**2, axis=1 )
        fps_cand.extend( keycfps )
        sums_cand.extend( sum_rss )
        if verb:
            print 'sum_rss: %s' % sum_rss
            print '-'*35

    # Location estimation.
    if len(fps_cand) > 1:
        # KNN
        # lst_set_sums_cand: list format for set of sums_cand.
        # bound_dist: distance boundary for K-min distances.
        lst_set_sums_cand =  np.array(list(set(sums_cand)))
        idx_bound_dist = np.argsort(lst_set_sums_cand)[:KNN][-1]
        bound_dist = lst_set_sums_cand[idx_bound_dist]
        idx_sums_sort = np.argsort(sums_cand)

        sums_cand = np.array(sums_cand)
        fps_cand = np.array(fps_cand)

        sums_cand_sort = sums_cand[idx_sums_sort]
        idx_bound_fp = np.searchsorted(sums_cand_sort, bound_dist, 'right')
        idx_sums_sort_bound = idx_sums_sort[:idx_bound_fp]
        #idxs_kmin = np.argsort(min_sums)[:KNN]
        sorted_sums = sums_cand[idx_sums_sort_bound]
        sorted_fps = fps_cand[idx_sums_sort_bound]
        if verb:
            print 'k-dists: \n%s\nk-locations: \n%s' % (sorted_sums, sorted_fps)
        # DKNN
        if sorted_sums[0]: 
            boundry = sorted_sums[0]*KWIN
        else: 
            if sorted_sums[1]:
                boundry = KWIN
                # What the hell are the following two lines doing here!
                #idx_zero_bound = np.searchsorted(sorted_sums, 0, side='right')
                #sorted_sums[:idx_zero_bound] = boundry / (idx_zero_bound + .5)
            else: boundry = 0
        idx_dkmin = np.searchsorted(sorted_sums, boundry, side='right')
        dknn_sums = sorted_sums[:idx_dkmin].tolist()
        dknn_fps = sorted_fps[:idx_dkmin]
        if verb: print 'dk-dists: \n%s\ndk-locations: \n%s' % (dknn_sums, dknn_fps)
        # Weighted_AVG_DKNN.
        num_dknn_fps = len(dknn_fps)
        if  num_dknn_fps > 1:
            coors = dknn_fps[:,1:3].astype(float)
            num_keyaps = np.array([ rsss.count('|')+1 for rsss in dknn_fps[:,-2] ])
            # ww: weights of dknn weights.
            ww = np.abs(num_keyaps - len_wlan).tolist()
            #print ww
            if not np.all(ww):
                if np.any(ww):
                    ww_sort = np.sort(ww)
                    #print 'ww_sort:' , ww_sort
                    idx_dknn_sums_sort = np.searchsorted(ww_sort, 0, 'right')
                    #print 'idx_dknn_sums_sort', idx_dknn_sums_sort
                    ww_2ndbig = ww_sort[idx_dknn_sums_sort] 
                    w_zero = ww_2ndbig / (len(ww)*ww_2ndbig)
                else:
                    w_zero = 1
                for idx,sum in enumerate(ww):
                    if not sum: ww[idx] = w_zero
            #print 'ww:', ww
            ws = np.array(ww) + dknn_sums
            weights = np.reciprocal(ws)
            if verb: print 'coors: \n%s\nweights: %s' % (coors, weights)
            posfix = np.average(coors, axis=0, weights=weights)
        else: posfix = np.array(dknn_fps[0][1:3]).astype(float)
        # ErrRange Estimation (more than 1 relevant clusters).
        idxs_clusters = idx_sums_sort_bound[:idx_dkmin]
        if len(idxs_clusters) == 1: 
            if maxNI == 1: poserr = 100
            else: poserr = 50
        else: 
            if verb:
                print 'idxs_clusters: %s' % idxs_clusters
                print 'all_pos_lenrss:'; pp.pprint(all_pos_lenrss)
            #allposs_dknn = np.vstack(np.array(all_pos_lenrss, object)[idxs_clusters])
            allposs_dknn = np.array(all_pos_lenrss, object)[idxs_clusters]
            if verb: print 'allposs_dknn:'; pp.pprint(allposs_dknn)
            poserr = np.average([ dist_km(posfix[1], posfix[0], p[1], p[0])*1000 
                for p in allposs_dknn ]) 
    else: 
        fps_cand = fps_cand[0][:-2]
        if verb: print 'location:\n%s' % fps_cand
        posfix = np.array(fps_cand[1:3]).astype(float)
        # ErrRange Estimation (only 1 relevant clusters).
        N_fp = len(keycfps)
        if N_fp == 1: 
            if maxNI == 1: poserr = 100
            else: poserr = 50
        else:
            if verb: 
                print 'posfix: %s' % posfix
                print 'all_pos_lenrss: '; pp.pprint(all_pos_lenrss)
            poserr = np.sum([ dist_km(posfix[1], posfix[0], p[1], p[0])*1000 
                for p in all_pos_lenrss ]) / (N_fp-1)
    ret = posfix.tolist()
    ret.append(poserr)
    if verb: print 'posresult: %s' % ret

    return ret


def main():
    try: opts, args = getopt.getopt(sys.argv[1:], 
            # NO backward compatibility for file handling, so the relevant 
            # methods(os,pprint)/parameters(addr_book,XXXPATH) 
            # imported from standard or 3rd-party modules can be avoided.
            "a:f:hv",
            ["algo=","fake","help","verbose"])
    except getopt.GetoptError:
        print 'Error: getopt!\n'
        usage(); sys.exit(99)

    # Program terminated when NO argument followed!
    #if not opts: usage(); sys.exit(0)

    # vars init.
    verbose = False; wlanfake = 0

    for o,a in opts:
        if o in ("-a", "--algo"):
            if a.isdigit():
                algoid = int(a)
                if algoid in range(1,3): 
                    print 'algo id: %s' % a;
                    continue
                else: pass
            else: pass
            print '\nInvalid algo id: %s\n'%a 
            usage(); sys.exit(99)
        elif o in ("-f", "--fake"):
            if a.isdigit(): 
                wlanfake = int(a)
                if wlanfake >= 0: continue
                else: pass
            else: pass
            print '\nIllegal fake WLAN scan ID: %s!' % a
            usage(); sys.exit(99)
        elif o in ("-h", "--help"):
            usage(); sys.exit(0)
        elif o in ("-v", "--verbose"):
            verbose = True
        else:
            print 'Parameter NOT supported: %s' % o
            usage(); sys.exit(99)


    # Get WLAN scanning results.
    len_visAPs, wifis = getWLAN(wlanfake)

    # Fix current position.
    if algoid == 1:
        posresult = fixPos_old(len_visAPs, wifis, verbose)
    elif algoid == 2:
        posresult = fixPos(len_visAPs, wifis, verbose)
    else: sys.exit('Invalid algoid: %s!' % algoid)
    if not posresult: sys.exit(99)
    print 'final posfix/poserr: \n%s' % posresult


if __name__ == "__main__":
    try:
        import psyco
        psyco.bind(scanWLAN_OS)
        psyco.bind(getWLAN)
        psyco.bind(fixPos)
        #psyco.full()
        #psyco.log()
        #psyco.profile(0.3)
    except ImportError:
        pass
    main()
    sys.exit(0)

    # log deails for diffs between cpp/py.
    import csv
    import pprint as pp
    import config as cfg
    diffs_csv = csv.reader( open(sys.argv[1],'r') )
    macrss = np.char.array([ line for line in diffs_csv ])[:,:2].split('|')
    for i in xrange(len(macrss)):
        print '%s TEST %d %s' % ('#'*30, i+1, '#'*30)
        macs = np.array(macrss[i,0]) 
        rsss = np.array(macrss[i,1])
        num_visAPs = len(macs)
        INTERSET = min(cfg.CLUSTERKEYSIZE, num_visAPs)
        idxs_max = np.argsort(rsss)[:INTERSET]
        mr = np.vstack((macs, rsss))[:,idxs_max]
        pp.pprint(mr)
        pyloc = fixPos(num_visAPs, mr, verb=True)
        print
