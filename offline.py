#!/usr/bin/env python
#coding=utf-8
#Parse GPS info by listening NMEA0183 GPGLL sentence from serial port.
from __future__ import division
from WLAN import wlanScan
from GPS import getGLL

#cmd='sudo iwlist wlan0 scan'.split()
gps = getGLL()
wlan = wlanScan()
gps.append(wlan)
print gps
