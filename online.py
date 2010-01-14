#!/usr/bin/env python
from __future__ import division
import os,sys,csv,getopt,string
from WLAN import scanWLAN
from pprint import pprint,PrettyPrinter
from config import DATPATH, RAWSUFFIX, RMPSUFFIX, KNN, INTERSET


def usage():
    print """
online.py - Copyleft 2009-2010 Yan Xiaotian, xiaotian.yan@gmail.com.
Location fingerprinting using deterministic/probablistic approaches.

usage:
    offline <option> <infile>
option:
    -i --infile          :  Input radio map file.
    -n --no-dump         :  No data dumping to file.
    -f --fake [for test] :  Fake WLAN scan results in case of bad WLAN coverage.
    -v --verbose         :  Verbose mode.
    -h --help            :  Show this help.
"""


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 
            "i:nfhv",
            ["infile=","no-dump","fake","help","verbose"])
    except getopt.GetoptError:
        usage()
        sys.exit(99)

    if not opts: usage(); sys.exit(0)

    # global vars init.
    times = 0; rmpfile = None; tfail = 0
    global verbose,pp,nodump,fake
    verbose = False; pp = None; nodump = False; fake = False

    for o,a in opts:
        if o in ("-i", "--infile"):
            if not os.path.isfile(a):
                print '\nRadio map file NOT exist: %s' % a
                sys.exit(99)
            elif not a:
                print '\nRadio map needed!\n'
                usage()
                sys.exit(99)
            else: 
                rmpfile = a
        elif o in ("-v", "--verbose"):
            verbose = True
            pp = PrettyPrinter(indent=2)
        elif o in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif o in ("-n", "--no-dump"):
            nodump = True
        elif o in ("-f", "--fake"):
            fake = True
        else:
            print 'Parameter NOT supported: %s' % o
            usage()
            sys.exit(99)

    if fake is True: 
        wlan = [ ['00:11:B5:FD:8B:6D', '-79'], ['00:15:70:9E:91:60', '-52'], 
                 ['00:15:70:9E:91:61', '-53'], ['00:15:70:9F:73:64', '-78'], 
                 ['00:15:70:9F:73:66', '-75'], ['00:15:70:9E:91:62', '-55'],
                 ['00:23:89:3C:BE:10', '-74'], ['00:23:89:3C:BE:11', '-78'], 
                 ['00:23:89:3C:BE:12', '-78'], ['00:11:B5:FE:8B:6D', '-80'], 
                 ['00:15:70:9E:6C:6C', '-65'], ['00:15:70:9E:6C:6D', '-70'],
                 ['00:15:70:9E:6C:6E', '-70'], ['00:15:70:9F:76:E0', '-81'], 
                 ['00:15:70:9F:7D:88', '-76'], ['00:15:70:9F:73:65', '-76'], 
                 ['00:23:89:3C:BD:32', '-75'], ['00:23:89:3C:BD:30', '-78'],
                 ['02:1F:3B:00:01:52', '-76'] ]
    else: 
        wlan = scanWLAN()

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
    pp.pprint(wlan)
    print 'len: %d\nmaxtemp:' % len(wlan)
    pp.pprint(maxtemp)

    pp.pprint(maxmacs)
    pp.pprint(maxrsss)


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
    if not rmpfile:
        print '\nRadio map needed!'
        usage()
        sys.exit(99)
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
    print 'macs_rmp: %s' % macs_rmp
    print 'rsss_rmp: %s' % rsss_rmp

    # Vectorized operation for Euclidean distance.
    #
    # 'rss_scan_dist' and 'rss_rmap_dist' contain rss of APs intersection  
    # between visible AP set from WLAN scanning and the AP set of each radio 
    # map fingerprint, these two vars are to be used for dist computation.
    mac_inters = []
    for i in range(len(macs_rmp)):
        mac_inters.append([])
        for j in range(len(maxmacs)):
            try:
                idx = list(macs_rmp[i]).index(maxmacs[j])
                mac_inters[i].append(maxmacs[j])
            except:
                #print '\nNotice: Cannot find %s in %s!\n' % (maxmacs[j], macs_rmp[i])
                break
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
    for i in range(len(macs_rmp)):
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
    k_idx_sort = idx_sort[:KNN]
    pp.pprint(sum_rss)
    pp.pprint(k_idx_sort)
    # ary_kmin: {spid:[ dist, [lat,lon] ]}
    ary_kmin = []
    for idx in k_idx_sort:
        ary_kmin.append( radiomap['spid'][idx] )
        ary_kmin.append( sum_rss[idx] )
        #ary_kmin.extend([ radiomap['lat'][idx],radiomap['lon'][idx] ])
        ary_kmin.extend( list(radiomap[idx])[1:3] ) #1,3: lat,lon row index in fp. 
    ary_kmin = np.array(ary_kmin).reshape(KNN,-1)

    pp.pprint(ary_kmin)
    sys.stdout.write('\nCentroid location of spid: %s: \n%s\n' % \
            ( sorted(list(ary_kmin[:,0])), tuple(ary_kmin[:,2:].mean(axis=0)) ) )

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
