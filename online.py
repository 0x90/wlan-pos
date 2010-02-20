#!/usr/bin/env python
from __future__ import division
import os,sys,getopt,string
from WLAN import scanWLAN_OS#, scanWLAN_RE
from pprint import pprint,PrettyPrinter
from config import KNN, CLUSTERKEYSIZE, WLAN_FAKE
#from address import addr_book


def usage():
    print """
online.py - Copyleft 2009-2010 Yan Xiaotian, xiaotian.yan@gmail.com.
Location fingerprinting using deterministic/probablistic approaches.

usage:
    offline <option> <infile>
option:
    -a --address=<key id>:  key id of address book configured in address.py.
                            <key id>: 1-cmri; 2-home.
    -f --fake=<mode id>  :  Fake WLAN scan results in case of bad WLAN coverage.
                            <mode id> 0:true scan; 1:cmri; 2:home.
    -v --verbose         :  Verbose mode.
    -h --help            :  Show this help.
example:
    #online.py -a 2 -v 
    #online.py -f 1 -v 
"""


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 
            # NO backward compatibility for file handling, so the relevant 
            # methods(os,pprint)/parameters(addr_book,XXXPATH) 
            # imported from standard or 3rd-party modules can be avoided.
            "a:f:hv",
            ["address=","fake","help","verbose"])
    except getopt.GetoptError:
        print 'Error: getopt!\n'
        usage(); sys.exit(99)

    if not opts: usage(); sys.exit(0)

    # global vars init.
    times = 0; rmpfile = None; tfail = 0
    interpart_offline = False; interpart_online = False
    #global verbose,pp,fake, addrid
    verbose = False; fake = 0; #addrid = 1; pp = None;

    for o,a in opts:
        if o in ("-a", "--address"):
            if a.isdigit(): 
                addrid = string.atoi(a)
                if 1 <= addrid <= 2: continue
                else: pass
            else: pass
            print '\nIllegal address id: %s!' % a
            usage()
            sys.exit(99)
        elif o in ("-f", "--fake"):
            if a.isdigit(): 
                fake = string.atoi(a)
                if 0 <= fake <= 2: continue
                else: pass
            else: pass
            print '\nIllegal fake GPS id: %s!' % a
            usage()
            sys.exit(99)
        elif o in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif o in ("-v", "--verbose"):
            verbose = True
            pp = PrettyPrinter(indent=2)
        else:
            print 'Parameter NOT supported: %s' % o
            usage()
            sys.exit(99)

    #if not rmpfile:
    #    print '\nRadio map needed!'
    #    usage()
    #    sys.exit(99)

    if fake == 0:   # True
        #wlan = scanWLAN_RE()
        wlan = scanWLAN_OS()
    else:           # CMRI or Home
        addrid = fake
        wlan = WLAN_FAKE[addrid]
    # Address book init.
    #addr = addr_book[addrid]

    len_scanAP = len(wlan)
    print 'Online visible APs: %d' % len_scanAP
    if len(wlan) == 0: sys.exit(0)   
    pp.pprint(wlan)

    INTERSET = min(CLUSTERKEYSIZE, len_scanAP)

    import numpy as np
    # All integers in rss field returned by scanWLAN_OS() 
    # are converted to strings during np.array(wlan).
    wlan = np.array(wlan).T
    rsss = wlan[1]
    maxidx = np.argsort(rsss)[:INTERSET]
    # Necessary for different list comprehension for maxmacs and maxrsss.
    # TBE:tobe explained.
    maxmacs = list(wlan[0,maxidx])
    maxrsss = [ string.atoi(rss) for rss in rsss[maxidx] ]
    print 'maxmacs:'; pp.pprint(maxmacs)
    print 'maxrsss: %s' % maxrsss


    import MySQLdb
    from config import db_config, tbl_names, SQL_SELECT, SQL_SELECT_WHERE
    try:
        conn = MySQLdb.connect(host = db_config['hostname'], 
                               user = db_config['username'], 
                             passwd = db_config['password'], 
                                 db = db_config['dbname'], 
                           compress = 1)
                        #cursorclass = MySQLdb.cursors.DictCursor)
    except MySQLdb.Error,e:
        print "\nCan NOT connect %s@server: %s!" % (username, hostname)
        print "Error(%d): %s" % (e.args[0], e.args[1])
        sys.exit(99)
    
    try:
        cursor = conn.cursor()
        table = tbl_names['cidaps']
        print 'select from table: %s' % table
        cursor.execute(SQL_SELECT % ('*', table))
        cidaps = cursor.fetchall()
    except MySQLdb.Error, e:
        print "Error(%d): %s" % (e.args[0], e.args[1])
        sys.exit(99)

    # cidaps: (('cid1', 'mac11|mac12|...'), ('cid2', 'mac21|mac22|...'), ...)
    #   cids: ['cid1', 'cid2', ...]
    # topaps: [['mac11', 'mac12', ...], ['mac21', 'mac22', ...], ...]
    cidaps = np.char.array(cidaps)
    cids = cidaps[:,0]
    topaps = cidaps[:,1].split('|')
    set_maxmacs = set(maxmacs)

    ##### lst_NOInter: array of the number of intersect APs between visible APs and all clusters.
    ########### maxNI: the maximum element of lst_NOInter.
    # idxs_maxNOInter: list of indices of clusters(in cids/topaps) with max intersect AP amount.
    lst_NOInter = np.array([ len(set_maxmacs & set(aps)) for aps in topaps ])
    idxs_sortedNOInter = np.argsort( lst_NOInter )
    maxNI = lst_NOInter[idxs_sortedNOInter[-1]]
    if maxNI == 0: # no intersection found
        print 'NO overlapping cluster found! Fingerprinting TERMINATED!'
        sys.exit(99)
    elif 0 < maxNI < 4:
        # size of intersection set < offline key AP set size:4, 
        # only keymacs/keyrsss (not maxmacs/maxrsss) need to be cut down.
        interpart_offline = True
        if maxNI < len_scanAP:
            # size of intersection set < online AP set size:len_scanAP, 
            # not only keymacs/keyrsss, but also maxmacs/maxrsss need to be cut down.
            interpart_online = True
            import copy as cp
        print 'Partly matched cluster(s) found! (max intersection size: %d)' % maxNI
    else: print 'Full matched cluster(s) found!' 
    idx_start = lst_NOInter[idxs_sortedNOInter].searchsorted(maxNI)
    idxs_maxNOInter = idxs_sortedNOInter[idx_start:]
    keys = [ [cids[idx], topaps[idx]] for idx in idxs_maxNOInter ]


    # Defected overlapping AP set solution thru loop.
    #keys = [ [cidaps[idx,0], aps] for idx,aps in enumerate(topaps) 
    #        if set_maxmacs == set(aps) ]
    #if not keys:
    #    print 'Exact matched cluster NOT found! Go on with subset search...'
    #    INTERS = INTERSET - 1
    #    keys = [ [cidaps[idx,0], aps] for idx,aps in enumerate(topaps)
    #            if len(set_maxmacs & set(aps)) == INTERS ]
    #    if not keys or INTERS == 0: 
    #        print 'Subset search FAILED! Fingerprinting TERMINATED!'
    #        sys.exit(99)
    #    else: print 'Subset keyed cluster(s) found: '
    #    interpart_offline = True
    #    import copy as cp
    #else: print 'Exact matched cluster(s) found: ' 
    pp.pprint(keys)

    # min_spids: [ [cid, spid, lat, lon, rsss], ... ]
    # min_sums: [ minsum1, minsum2, ... ]
    min_spids = []; min_sums = []
    for cid,keyaps in keys:
        try:
            # Returns values identified by field name(or field order if no arg).
            table = tbl_names['cfps']
            state_where = 'cid = %s' % cid
            print 'select %s from table %s' % (state_where, table)
            cursor.execute(SQL_SELECT_WHERE % ('*' , table, state_where))
            keycfps = cursor.fetchall()
        except MySQLdb.Error,e:
            print "Error(%d): %s" % (e.args[0], e.args[1])
            cursor.close(); conn.close()
            sys.exit(99)
        print ' keyaps: %s' % keyaps
        print 'keycfps: %s' % keycfps
        # Fast fix when the ONLY 1 cid selected in 'cidaps' has 1 spid selected in 'cfps'.
        if len(keys) == 1 and cursor.rowcount == 1:
            min_spids = keycfps
            break
        keyrsss = np.char.array(keycfps)[:,4].split('|')
        keyrsss = np.array([ [string.atof(rss) for rss in spid] for spid in keyrsss ])
        # Rearrange key MACs/RSSs in 'keyrsss' in according to intersection set 'keyaps'.
        if interpart_offline is True:
            if interpart_online is True:
                mmacs = cp.deepcopy(maxmacs); mrsss = cp.deepcopy(maxrsss)
                rm_idx = maxmacs.index(list(set_maxmacs - (set_maxmacs&set(keyaps)))[0])
                mmacs.pop(rm_idx); mrsss.pop(rm_idx)
            else: mmacs = maxmacs; mrsss = maxrsss
            take_idx = [ keyaps.index(x) for x in mmacs ]
            print '  mmacs: %s\tmrsss: %s' % (mmacs, mrsss)
            keyrsss = keyrsss.take(take_idx, axis=1)
        else: mrsss = maxrsss
        # Euclidean dist solving and sorting.
        rss_dist = ( mrsss - keyrsss )**2
        sum_rss = rss_dist.sum(axis=1)
        print 'sum_rss: %s' % sum_rss
        idx_min = sum_rss.argmin()
        min_spids.append(list(keycfps[idx_min]))
        min_sums.append(sum_rss[idx_min])
        print '-'*60


    if len(min_spids) > 1:
        idxs_kmin = np.argsort(min_sums)[:KNN]
        min_spids = np.array(min_spids).reshape(-1,5)
        print 'dists: '; print np.array(min_sums)[idxs_kmin]
        print 'locations: '; print min_spids[idxs_kmin]
    else:
        print 'location: %s' % min_spids

    cursor.close()
    conn.close()
    sys.exit(0)


    # Deprecated: radio map file related operation code that is no longer used.
    # NOTE:
    #   The `numpy.core.defchararray` exists for backwards compatibility with
    #   Numarray, it is not recommended for new development. If one needs
    #   arrays of strings, use arrays of `dtype` `object_`, `string_` or
    #   `unicode_`, and use the free functions in the `numpy.char` module
    #   for fast *vectorized string operations*.
    #   chararrays should be created using `numpy.char.array` or
    #   `numpy.char.asarray`, rather than `numpy.core.defchararray` directly.
    #
    # FIXME: usecols for only spid-macs-rsss picking failed.
    radiomap = np.loadtxt(rmpfile, dtype=np.dtype(dt_rmp_nocluster), delimiter=',')
    macs_rmp = np.char.array(radiomap['macs']).split('|')
    # rsss_rmp may contain fingerprints that has more than INTERSET elements 
    # because of the lower storage precision in radio map, which is evaluated 
    # by far NOT to affect the whole. 
    # One possible way to fix this might to modify this line of code:
    # rss_rmap_dist[i].append(string.atof(rsss_rmp[i][idx]))
    # to be like the following line, which is not yet verified.
    # rss_rmap_dist[i].append(string.atof(rsss_rmp[:,:INTERSET][i][idx]))
    rsss_rmp = np.char.array(radiomap['rsss']).split('|')
    #print 'macs_rmp: %s' % macs_rmp
    #print 'rsss_rmp: %s' % rsss_rmp

    # K_NN takes minimum value between KNN and number of fingerprints in case of 
    # mal-assignment of ary_kmin when there are not enough KNN fingerprints.
    len_rmp = len(macs_rmp)
    if len_rmp < 2 or not isinstance(macs_rmp[0], list):
        print '\nNot enough(>1) fingerprints in radio map: %s!\n' % rmpfile
        sys.exit(99)
    K_NN = min( KNN, len_rmp )

    # Vectorized operation for Euclidean distance.
    #
    # 'rss_scan_dist' and 'rss_rmap_dist' contain rss of APs intersection  
    # between visible AP set from WLAN scanning and the AP set of each radio 
    # map fingerprint, these two vars are to be used for dist computation.
    mac_inters = []
    for i in range(len_rmp):
        mac_inters.append([])
        for j in range(len(maxmacs)):
            try:
                idx = list(macs_rmp[i]).index(maxmacs[j])
                mac_inters[i].append(maxmacs[j])
            except:
                #print '\nNotice: Cannot find %s in %s!\n' % (maxmacs[j], macs_rmp[i])
                continue
        #print 'mac_inters: '; pp.pprint(mac_inters)
        #print '-'*65
    #print 'mac_inters: '; pp.pprint(mac_inters)

    # Solve final mac_inter ready for distance computation.
    inter = set( mac_inters.pop() )
    while not len(mac_inters) is 0:
        inter = inter & set(mac_inters.pop())
    mac_inter = list(inter)
    if len(mac_inter) == 0:
        print '\nError: NO common AP(s) of (all FPs) & (scanned) found!'
        sys.exit(99)
    print 'mac_inter:'; pp.pprint(mac_inter)

    rss_scan_dist = []
    rss_rmap_dist = []
    for i in range(len_rmp):
        rss_scan_dist.append([])
        rss_rmap_dist.append([])
        for mac in mac_inter:
            try:
                idx_rmap = list(macs_rmp[i]).index(mac)
                idx_scan = maxmacs.index(mac)
                rss_scan_dist[i].append(maxrsss[idx_scan])
                rss_rmap_dist[i].append(string.atof(rsss_rmp[i][idx_rmap]))
            except:
                print '\nError: Cannot find %s in %s!\n' % (mac, macs_rmp[i])
                if not len(rss_scan_dist[i]) == 0:
                    rss_scan_dist.pop(i) 
                if not len(rss_rmap_dist[i]) == 0:
                    rss_rmap_dist.pop(i)
                break
        #print 'rss_scan_dist: %s' % rss_scan_dist
        #print 'rss_rmap_dist: %s' % rss_rmap_dist
        #print '-'*65

    rss_scan_dist = np.array(rss_scan_dist)
    rss_rmap_dist = np.array(rss_rmap_dist)
    print 'rss_scan_dist: '; pp.pprint(rss_scan_dist)
    print 'rss_rmap_dist: '; pp.pprint(rss_rmap_dist)

    rss_dist = ( rss_scan_dist - rss_rmap_dist )**2
    #print 'squared rss distance: '; pp.pprint(rss_dist)

    sum_rss = rss_dist.sum(axis=1)
    # idx_sort: index array of sorted sum_rss.
    idx_sort = sum_rss.argsort()
    k_idx_sort = idx_sort[:K_NN]
    print 'k_idx_sort:'; pp.pprint(k_idx_sort)
    # ary_kmin: {spid:[ dist, [lat,lon] ]}
    ary_kmin = []
    #addr_kmin = []
    for idx in k_idx_sort:
        spidx = radiomap['spid'][idx]
        ary_kmin.append( spidx )
        ary_kmin.append( sum_rss[idx] )
        #ary_kmin.extend([ radiomap['lat'][idx],radiomap['lon'][idx] ])
        ary_kmin.extend( list(radiomap[idx])[1:3] ) #1,3: lat,lon row index in fp. 
        #addr_kmin.append( addr[spidx] )
    ary_kmin = np.array(ary_kmin).reshape(K_NN,-1)

    print 'ary_kmin:'; pp.pprint(ary_kmin)

    print '\nKNN spid(s): %s' % str( list(ary_kmin[:,0]) )
    #print 'Address: %s' % addr_kmin
    print 'Centroid location: %s\n' % str( tuple(ary_kmin[:,2:].mean(axis=0)) )


    #TODO:optimize sort routine with both indices and vals retuened.
    #
    # np.argsort(a, axis=-1, kind='quicksort', order=None)
    # Returns the indices that would sort an array.
    # 
    # Perform an indirect sort along the given axis using the algorithm specified
    # by the `kind` keyword. It returns an array of indices of the same shape as
    # `a` that index data along the given axis in sorted order.
    #
    # Parameters
    # ----------
    # a : array_like
    #     Array to sort.
    # axis : int or None, optional
    #     Axis along which to sort.  The default is -1 (the last axis). If None,
    #     the flattened array is used.
    # kind : {'quicksort', 'mergesort', 'heapsort'}, optional
    #     Sorting algorithm.
    # order : list, optional
    #     When `a` is an array with fields defined, this argument specifies
    #     which fields to compare first, second, etc.  Not all fields need be
    #     specified.
    #
    # Returns
    # -------
    # index_array : ndarray, int
    #     Array of indices that sort `a` along the specified axis.
    #     In other words, ``a[index_array]`` yields a sorted `a`.


if __name__ == "__main__":
    try:
        import psyco
        psyco.bind(scanWLAN_OS)
        #psyco.full()
        #psyco.log()
        #psyco.profile(0.3)
    except ImportError:
        pass
    main()
