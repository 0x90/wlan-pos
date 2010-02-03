#!/usr/bin/env python
from __future__ import division
import os,sys,csv,getopt,string
from WLAN import scanWLAN
from pprint import pprint,PrettyPrinter
from config import DATPATH, RAWSUFFIX, RMPSUFFIX, \
                KNN, CLUSTERKEYSIZE, WLAN_FAKE, dt_rmp_nocluster
from address import addr_book


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
    -i --infile          :  Input raw or clustered(not avail) radio map file.
    -v --verbose         :  Verbose mode.
    -h --help            :  Show this help.
example:
    #online.py -a 2 -v -i /path/to/some/rmpfile
    #online.py -f 2 -v -i /path/to/some/rmpfile
"""


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 
            "a:i:nf:hv",
            ["address=","infile=","no-dump","fake","help","verbose"])
    except getopt.GetoptError:
        usage()
        sys.exit(99)

    if not opts: usage(); sys.exit(0)

    # global vars init.
    times = 0; rmpfile = None; tfail = 0
    global verbose,pp,nodump,fake, addrid
    verbose = False; pp = None; nodump = False; fake = 0; addrid = 1

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
        if o in ("-i", "--infile"):
            if not os.path.isfile(a):
                print '\nRadio map file NOT exist: %s' % a
                sys.exit(99)
            elif not a:
                print '\nRadio map needed!\n'
                usage()
                sys.exit(99)
            else: rmpfile = a
        elif o in ("-v", "--verbose"):
            verbose = True
            pp = PrettyPrinter(indent=2)
        elif o in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif o in ("-f", "--fake"):
            if a.isdigit(): 
                fake = string.atoi(a)
                if 0 <= fake <= 2: continue
                else: pass
            else: pass
            print '\nIllegal fake GPS id: %s!' % a
            usage()
            sys.exit(99)
        else:
            print 'Parameter NOT supported: %s' % o
            usage()
            sys.exit(99)

    #if not rmpfile:
    #    print '\nRadio map needed!'
    #    usage()
    #    sys.exit(99)

    if fake == 0:   # True
        wlan = scanWLAN()
    else:           # CMRI or Home
        addrid = fake
        wlan = WLAN_FAKE[addrid]
    # Address book init.
    #addr = addr_book[addrid]

    len_scanAP = len(wlan)
    print 'Online visible APs: %d' % len_scanAP
    pp.pprint(wlan)

    # 
    INTERSET = min(CLUSTERKEYSIZE, len_scanAP)

    import numpy as np
    wlan = np.array(wlan).T
    rsss = wlan[1]
    maxidx = np.argsort(rsss)[:INTERSET]
    maxmacs = list(wlan[0][:,maxidx])
    maxrsss = [ string.atoi(rss) for rss in rsss[:,maxidx] ]

    #maxrsss = []
    #maxmacs = []
    #maxtemp = sorted( [string.atoi(ap[1]) for ap in wlan], reverse=True )[:INTERSET]
    ##maxtemp = [-52, -53, -55, -65, -70, -70]
    #print 'maxtemp: %s' % maxtemp

    #cnt = 0
    #for ap in wlan:
    #    cnt += 1
    #    if ( len(maxmacs)>=INTERSET ) and ( maxrsss[:INTERSET]==maxtemp ):
    #        print 'Bravo! maxtemp matched!'
    #        break
    #    newrss = string.atoi(ap[1])
    #    if (not len(maxrsss) == 0) and (newrss > maxrsss[-1]):
    #        maxrsss.insert(-1, newrss)
    #        maxrsss.sort(reverse=True)
    #        idx = maxrsss.index(newrss)
    #        maxmacs.insert(idx, ap[0])
    #    else: 
    #        maxrsss.append(newrss)
    #        maxmacs.append(ap[0])
    #    #print 'cnt: %d' % cnt
    #    #print 'maxmacs: %s' % maxmacs
    #    #print 'maxrsss: %s' % maxrsss
    #    #print '-'*65

    #maxmacs = maxmacs[:INTERSET]
    #maxrsss = maxrsss[:INTERSET]

    print 'maxmacs:'; pp.pprint(maxmacs)
    print 'maxrsss: %s' % maxrsss


    import MySQLdb
    from config import hostname, username, password, dbname, \
                       tbl_names, SQL_SELECT, SQL_SELECT_WHERE
    try:
        conn = MySQLdb.connect(host=hostname, user=username, \
                passwd=password, db=dbname, compress=1)
                #cursorclass=MySQLdb.cursors.DictCursor)
    except MySQLdb.Error,e:
        print "\nCan NOT connect %s@server: %s!" % (username, hostname)
        print "Error(%d): %s" % (e.args[0], e.args[1])
        sys.exit(99)
    
    try:
        cursor = conn.cursor()
        table = tbl_names['cidaps']
        print 'select from table: %s' % table
        cursor.execute(SQL_SELECT % ('*' ,table))
        cidaps = cursor.fetchall()
    except MySQLdb.Error,e:
        print "Error(%d): %s" % (e.args[0], e.args[1])
        sys.exit(99)

    #FIXME: set_maxmacs INCLUDED or EQUAL TO set(aps) should all be considered.
    # Fingerprints in same cluster should have same order for RSSs according to key MACs:
    # Though keyaps is logically defined and used as a SET, it's stored as ordered list.
    cidaps = np.char.array(cidaps)
    topaps = cidaps[:,1].split('|')
    set_maxmacs = set(maxmacs)
    keys = [ [cidaps[idx,0], aps] for idx,aps in enumerate(topaps) 
            if set_maxmacs == set(aps) ]
    print 'clusters found: '; pp.pprint(keys)

    #num_clusters = len(keys)
    ## state_where construction.
    #if not len_keycids == 0: 
    #    if len_keycids == 1:
    #        state_where = 'cid in (%s)' % keycids[0]
    #    else:
    #        state_where = 'cid in %s' % str(tuple(keycids))
    #else:
    #    print 'Oops! no proper cluster found!'
    #    cursor.close(); conn.close()
    #    sys.exit(99)

    # min_spidrss: [[cid,spid,lat,lon,rssss,min_rss],...]
    min_spidrss = []
    for cid,keyaps in keys:
        try:
            # Returns values identified by field name(or field order if no arg).
            table = tbl_names['cfps']
            print 'select from table: %s' % table
            state_where = 'cid = %s' % cid
            cursor.execute(SQL_SELECT_WHERE % ('*' , table, state_where))
            keycfps = cursor.fetchall()
        except MySQLdb.Error,e:
            print "Error(%d): %s" % (e.args[0], e.args[1])
            cursor.close(); conn.close()
            sys.exit(99)
        print 'cid: %s, keyaps: %s' % (cid, keyaps)
        print 'keycfps: '; pp.pprint(keycfps)

        maxmacs_idx = [ keyaps.index(x) for x in maxmacs ]
        maxrsss = np.array([ maxrsss[i] for i in maxmacs_idx ])
        print 'maxrsss: '; pp.pprint(maxrsss)

        keyrsss_tmp = np.char.array(keycfps)[:,4].split('|')
        # 3 line of ugly element-wise atof code coming up.
        keyrsss = []
        for i in range(len(keycfps)):
            keyrsss.append([ string.atof(x) for x in keyrsss_tmp[i] ])
        keyrsss = np.array(keyrsss)
        print 'keyrsss: '; pp.pprint(keyrsss)

        rss_dist = ( maxrsss - keyrsss )**2
        print 'squared rss distance: '; pp.pprint(rss_dist)

        sum_rss = rss_dist.sum(axis=1)
        print 'sum_rss: '; pp.pprint(sum_rss)
        idx_min = sum_rss.argmin()
        min_rss = sum_rss[idx_min]
        print 'idx_min: %d, min_rss: %f' % (idx_min, min_rss)
        spidrss = list(keycfps[idx_min])
        spidrss.append(min_rss)
        min_spidrss.append( spidrss )


    if len(min_spidrss) > 1:
        idxs_kmin = np.argsort([ spid[5] for spid in min_spidrss ])[:K_NN]
        pp.pprint(min_spidrss[idxs_kmin])
    else:
        pp.pprint(min_spidrss)

    cursor.close()
    conn.close()
    sys.exit(0)

    # NOTE:
    #   The `numpy.core.defchararray` exists for backwards compatibility with
    #   Numarray, it is not recommended for new development. If one needs
    #   arrays of strings, use arrays of `dtype` `object_`, `string_` or
    #   `unicode_`, and use the free functions in the `numpy.char` module
    #   for fast *vectorized string operations*.
    #   chararrays should be created using `numpy.char.array` or
    #   `numpy.char.asarray`, rather than `numpy.core.defchararray` directly.
    #
    #FIXME: usecols for only spid-macs-rsss picking failed.
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
    main()
