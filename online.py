#!/usr/bin/env python
from __future__ import division
import os,sys,csv,getopt,string
from WLAN import scanWLAN
from pprint import pprint,PrettyPrinter
from config import DATPATH, RAWSUFFIX, RMPSUFFIX


def usage():
    print """
online.py - Copyleft 2009-2010 Yan Xiaotian, xiaotian.yan@gmail.com.
Location fingerprinting using deterministic/probablistic approaches.

usage:
    offline <option> <infile>
option:
    -i --infile          :  Input radio map file.
    -n --no-dump         :  No data dumping to file.
    -f --fake [for test] :  Fake WLAN scan results for bad coverage conditions.
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

    #TODO:dict implementation of 6 max-rss ap selection.
    maxrsss = []
    maxmacs = []
    maxtemp = sorted( [string.atoi(ap[1]) for ap in wlan], reverse=True )[:6]
    #maxtemp = [-52, -53, -55, -65, -70, -70]

    cnt = 0
    for ap in wlan:
        cnt += 1
        if len(maxmacs) >= 6:
            if maxrsss[:6] == maxtemp:
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
        if verbose is True:
            print 'cnt: %d' % cnt
            print 'maxmacs: %s' % maxmacs
            print 'maxrsss: %s' % maxrsss
            print '-'*65

    maxmacs = maxmacs[:6]
    maxrsss = maxrsss[:6]
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
    # String length of 107 and 89 chars are used for each intersection set to have 
    # at most 6 APs, which should be enough for classification, very ugly though.
    dt = np.dtype( {'names':('spid','lat','lon','macs','rsss'),
                  'formats':('i4','f4','f4','S107','S89')} )
    #FIXME: usecols for only spid-macs-rsss picking failed.
    if not rmpfile:
        print '\nRadio map needed!'
        usage()
        sys.exit(99)
    radiomap = np.loadtxt(rmpfile, dtype=dt, delimiter=',')
    macs_rmp = np.char.array(radiomap['macs']).split('|')
    rsss_rmp = np.char.array(radiomap['rsss']).split('|')
    print 'macs_rmp: %s' % macs_rmp
    print 'rsss_rmp: %s' % rsss_rmp

    # Vectorized operation for Euclidean distance.
    #
    # rss_scan_dist and rss_rmap_dist contain rss of intersection APs between visible 
    # AP set from WLAN scanning and the AP set of each radio map fingerprint record, 
    # these two vars are to be used for dist computation.
    #
    #TODO: determination of which fingerprint to pick.
    rss_scan_dist = []
    rss_rmap_dist = []
    for i in range(len(macs_rmp)):
        rss_scan_dist.append([])
        rss_rmap_dist.append([])
        for j in range(len(maxmacs)):
            print 'rss_scan_dist: %s' % rss_scan_dist
            print 'rss_rmap_dist: %s' % rss_rmap_dist
            try:
                idx = list(macs_rmp[i]).index(maxmacs[j])
                rss_scan_dist[i].append(maxrsss[j])
                rss_rmap_dist[i].append(string.atof(rsss_rmp[i][idx]))
            except:
                rss_scan_dist[i].append(0)
                rss_rmap_dist[i].append(0)
            print '-'*60
        print '='*65

    pp.pprint(rss_scan_dist)
    pp.pprint(rss_rmap_dist)

    rss_scan_dist = np.array(rss_scan_dist)
    rss_rmap_dist = np.array(rss_rmap_dist)

    pp.pprint(rss_scan_dist)
    pp.pprint(rss_rmap_dist)
    rss_dist = (rss_scan_dist - rss_rmap_dist)**2
    pp.pprint(rss_dist)

    rss_min = min(rss_dist.sum(axis=1))
    print rss_min






if __name__ == "__main__":
    main()
