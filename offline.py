#!/usr/bin/env python
#coding=utf-8
#Parse GPS info by listening NMEA0183 GPGLL sentence from serial port.
from __future__ import division
import sys
from WLAN import scanWLAN
from GPS import getGPS

gps = getGPS()
wlan = scanWLAN()

from pprint import pprint,PrettyPrinter
pp = PrettyPrinter(indent=2)
pp.pprint(wlan)

# For list/field separation of the WLAN scan results.
# ';' separates the different AP scan result lists.
# '|' separates the detailed data fields in each AP scan results.
aps = [ ';'.join([ '|'.join(ap) for ap in wlan ]) ]
gps.extend(aps)

ofile = open('out','a')
ofile.write(str(gps)+'\n')


sys.exit(0)
iscan = eval(open('out','r').readline())
print iscan
print 'time: %s\nLatLon: %f/%f\n%s\n' % \
        (iscan[0], iscan[1], iscan[2], iscan[3])
aps = iscan[3].split(';')
for ap in aps:
    print ap.split('|')

sys.exit(0)
import csv
csvout = csv.writer( open('out.csv','wb'), delimiter=',' )
csvout.writerows(gps)

