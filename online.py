#!/usr/bin/env python
from __future__ import division
import os,sys,csv,getopt,string
from WLAN import scanWLAN
from pprint import pprint,PrettyPrinter
from config import DATPATH, RAWSUFFIX, RMPSUFFIX, \
                KNN, INTERSIZE, WLAN_FAKE
from address import addr_book


def usage():
    print """
online.py - Copyleft 2009-2010 Yan Xiaotian, xiaotian.yan@gmail.com.
Location fingerprinting using deterministic/probablistic approaches.

usage:
    offline <option> <infile>
option:
    -a --address=<key id>:  key id of address book configured in address.py.
                            <key id>: 1-cmri(default); 2-home.
    -f --fake=<mode id>  :  Fake WLAN scan results in case of bad WLAN coverage.
                            <mode id> 0:true scan(default); 1:cmri; 2:home.
    -i --infile          :  Input radio map file.
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

    if not rmpfile:
        print '\nRadio map needed!'
        usage()
        sys.exit(99)

    if fake == 0:   # True
        wlan = scanWLAN()
    else:           # CMRI or Home
        addrid = fake
        wlan = WLAN_FAKE[addrid]
    # Address book init.
    addr = addr_book[addrid]

    len_scanAP = len(wlan)
    print 'Online scanned APs: %d' % len_scanAP
    pp.pprint(wlan)

    # 
    INTERSET = min(INTERSIZE, len_scanAP)

    # dict implementation of INTERSET max-rss ap selection.
    maxrsss = []
    maxmacs = []
    maxtemp = sorted( [string.atoi(ap[1]) for ap in wlan], reverse=True )[:INTERSET]
    #maxtemp = [-52, -53, -55, -65, -70, -70]

    cnt = 0
    for ap in wlan:
        cnt += 1
        if len(maxmacs) >= INTERSET:
            if maxrsss[:INTERSET] == maxtemp:
                print 'Bravo! maxtemp matched!'
                break
        newrss = string.atoi(ap[1])
        if not len(maxrsss) == 0:
            if newrss > maxrsss[-1]:
                maxrsss.insert(-1, newrss)
                maxrsss.sort(reverse=True)
                idx = maxrsss.index(newrss)
                maxmacs.insert(idx, ap[0])
            else:
                maxrsss.append(newrss)
                maxmacs.append(ap[0])
        else:
            maxrsss.append(newrss)
            maxmacs.append(ap[0])
        #print 'cnt: %d' % cnt
        #print 'maxmacs: %s' % maxmacs
        #print 'maxrsss: %s' % maxrsss
        #print '-'*65

    maxmacs = maxmacs[:INTERSET]
    maxrsss = maxrsss[:INTERSET]
    print 'maxtemp: %s' % maxtemp

    print 'maxmacs:'; pp.pprint(maxmacs)
    print 'maxrsss:'; pp.pprint(maxrsss)


    import numpy as np
    #
    # NOTE:
    #   The `numpy.core.defchararray` exists for backwards compatibility with
    #   Numarray, it is not recommended for new development. If one needs
    #   arrays of strings, use arrays of `dtype` `object_`, `string_` or
    #   `unicode_`, and use the free functions in the `numpy.char` module
    #   for fast vectorized string operations.
    #   chararrays should be created using `numpy.char.array` or
    #   `numpy.char.asarray`, rather than `numpy.core.defchararray` directly.
    #
    # String length of 179 and 149 chars are used for each intersection set to have 
    # at most INTERSET APs, which should be enough for classification, very ugly though.
    dt = np.dtype( {'names':('spid','lat','lon','macs','rsss'),
                  'formats':('i4','f4','f4','S179','S149')} )
    #FIXME: usecols for only spid-macs-rsss picking failed.
    radiomap = np.loadtxt(rmpfile, dtype=dt, delimiter=',')
    macs_rmp = np.char.array(radiomap['macs']).split('|')
    # rsss_rmp may contain some fingerprints that has more than INTERSET elements 
    # because of the lower precision in radio map, which is considered by far 
    # NOT to affect the whole. 
    # One possible way to fix this might to modify this line of code:
    # rss_rmap_dist[i].append(string.atof(rsss_rmp[i][idx]))
    # to be like the following line, which is not yet verified.
    # rss_rmap_dist[i].append(string.atof(rsss_rmp[:INTERSET][i][idx]))
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
    print 'mac_inter'; pp.pprint(mac_inter)

    rss_scan_dist = []
    rss_rmap_dist = []
    for i in range(len_rmp):
        rss_scan_dist.append([])
        rss_rmap_dist.append([])
        for j in range(len(mac_inter)):
            try:
                idx = list(macs_rmp[i]).index(mac_inter[j])
                rss_scan_dist[i].append(maxrsss[j])
                rss_rmap_dist[i].append(string.atof(rsss_rmp[i][idx]))
            except:
                print '\nError: Cannot find %s in %s!\n' % (maxmacs[j], macs_rmp[i])
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
    addr_kmin = []
    for idx in k_idx_sort:
        spidx = radiomap['spid'][idx]
        ary_kmin.append( spidx )
        ary_kmin.append( sum_rss[idx] )
        #ary_kmin.extend([ radiomap['lat'][idx],radiomap['lon'][idx] ])
        ary_kmin.extend( list(radiomap[idx])[1:3] ) #1,3: lat,lon row index in fp. 
        addr_kmin.append( addr[spidx] )
    ary_kmin = np.array(ary_kmin).reshape(K_NN,-1)

    print 'ary_kmin:'; pp.pprint(ary_kmin)

    print '\nKNN spid(s): %s' % str( list(ary_kmin[:,0]) )
    print 'Address: %s' % addr_kmin
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
