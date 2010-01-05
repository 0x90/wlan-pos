#!/usr/bin/env python
#coding=utf-8
#Parse GPS info by listening NMEA0183 GPGLL sentence from serial port.
from __future__ import division
import sys,csv,getopt,string
from time import strftime
from WLAN import scanWLAN
from GPS import getGPS
from pprint import pprint,PrettyPrinter
from config import DATPATH, RAWSUFIX


def getRAW():
    """
    Collecting scanning results for WLAN & GPS.
    """
    timestamp = strftime('%Y%m%d-%H%M%S')
    #FIXME:exception handling
    #rawdata = getGPS(); 
    rawdata = [ 116.472673167, 39.9229416667 ]
    rawdata.insert(0,timestamp)
    #FIXME:exception handling
    wlan = scanWLAN()
    #wlan = [ [ '00:0B:6B:3C:75:34','-89' ] , [ '00:25:86:23:A4:48','-86' ] ]
    #wlan = [ [] ]

    # Raw data: time, lat, lon, mac1|mac2, rss1|rss2
    # aps: [ [mac1, mac2], [rss1, rss2] ]
    # aps_raw: [ mac1|mac2, rss1|rss2 ]
    num_fields = len(wlan[0])
    if not num_fields == 0:
        aps = [ [ ap[i] for ap in wlan ] for i in range(num_fields) ]
        aps_raw = [ '|'.join(ap) for ap in aps ]
        rawdata.extend(aps_raw)

    return rawdata


def usage():
    print """
offline.py - Copyright 2009 Yan Xiaotian@CMRI
Offline calibration & preprocessing for radio map generation.

usage:
    offline <option> <infile>
option:
    -s --scan=<times> :  Scan for <times> times and log in raw file. 
    -r --rmap=<infile>:  Process the given raw data to radio map. 
    -a --aio          :  All in one, get raw data, followed by processing it to radio map.
    -i --spid=<spid>  :  Sampling point id. (<spid>default:spid+1, 'spid' in log/spid).
    -v --verbose      :  Verbose mode.
    -h --help         :  Show this help.
"""

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 
                "s:r:ai:hv",
                ["scan=", "rmap=", "aio", "spid=", "help", "verbose"])
    except getopt.GetoptError:
        usage()
        sys.exit(99)
    #print opts

    if not opts: usage()
    for o,a in opts:
        if o in ("-i", "--spid"):
            if a:
                spid = string.atoi(a)
            else:
                #FIXME: default spid handling.
                spid = 1
        elif o in ("-s", "--scan"):
            if a.isdigit: times = string.atoi(a)
            else: times = 1

            for i in range(times):
                print "Survey: %d" % (i+1)
                rawdata = getRAW()
                # Raw data: spid, time, lat, lon, mac1|mac2, rss1|rss2
                rawdata.insert(0,spid)
                pp = PrettyPrinter(indent=2)
                pp.pprint(rawdata)

                date = strftime('%Y-%m%d')
                rawfile = open(DATPATH + date + ('-%06d' % spid) + RAWSUFIX, 'a')
                rawout = csv.writer( rawfile )
                rawout.writerow(rawdata)
        #elif o in ("-r", "--rmap"):
        #elif o in ("-a", "--aio"):
        #elif o in ("-v", "--verbose"):
        elif o in ("-h", "--help", " "):
            usage()
            sys.exit(0)
        else:
            assert False, "Unhandled option"


if __name__ == "__main__":
    main()

