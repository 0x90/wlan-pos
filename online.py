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
                print 'Radio map file NOT exist: %s' % a
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

    #if fake is True: wlan = [ [ '00:0B:6B:3C:75:34','-89' ] , [ '00:25:86:23:A4:48','-86' ] ]
    #else: wlan = scanWLAN(); 

    from numpy import loadtxt, dtype, fromfile

    dt = dtype( {'names':('spid','lat','lon','mac','rss'),
               'formats':('i4',  'f4', 'f4', 'S35','S20')} )
    #FIXME: usecols failed.
    radiomap = loadtxt(rmpfile, dtype=dt, delimiter=',')

    pp.pprint(radiomap['mac'])
    pp.pprint(radiomap['rss'])

if __name__ == "__main__":
    main()
