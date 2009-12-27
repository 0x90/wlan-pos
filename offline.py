#!/usr/bin/env python
#coding=utf-8
#Parse GPS info by listening NMEA0183 GPGLL sentence from serial port.
from __future__ import division
from WLAN import scanWLAN
from GPS import getGPS
from pprint import pprint,PrettyPrinter

#cmd='sudo iwlist wlan0 scan'.split()
gps = getGPS()
wlan = scanWLAN()
gps.append(wlan)
pp = PrettyPrinter(indent=2)
pp.pprint(gps)
