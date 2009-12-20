#!/usr/bin/env python
#coding=utf-8
#Parse GPS info by listening NMEA0183 GPGLL sentence from serial port.
from __future__ import division
import serial,string
from time import sleep

def getGLL():
    """
    Bluez likes to use /dev/rfcomm0, but pyserial uses /dev/ttyS*.
    So be noticed to redirect rfcomm0 to ttyS* with following cmds:
    sudo rm /dev/ttyS0 -f && ln -s /dev/rfcomm0 /dev/ttyS0.
    """
    ser = serial.Serial()
    ser.port = 0
    ser.baudrate = 4800
    ser.open()

    while True:
        line = ser.readline()
        if not line.startswith('$GPGLL,'):
            continue

        #Sentence NAME,Latitude,NS,Longitude,EW,Time(UTC),Active,Checksum.
        sentence = line.split(',') 
        if len(sentence) != 8: continue
        #print line

        # Format of sentence[5](utc): hhmmss
        time = string.atof(sentence[5])
        #hour = int(time/10000)
        #min = int(time/100)-hour*100
        #sec = int(time)-hour*10000-min*100

        lat_tmp = string.atof(sentence[1])
        lat_int = int(lat_tmp/100)
        lat = lat_int + (lat_tmp - lat_int*100)/60
        lon_tmp = string.atof(sentence[3])
        lon_int = int(lon_tmp/100)
        lon = lon_int + (lon_tmp - lon_int*100)/60

        # Display of Details
        #print 'Time: %d:%d:%d, Lat: %f%s Lon: %f%s' % \
        #        (hour+8, min, sec, lat, sentence[2], lon, sentence[4])

        gll = [ time + 8*10000, lon, lat, sentence[2] + sentence[4] ]
        break

    #sleep(.2)
    ser.close()
    return gll

if __name__ == "__main__":
    print getGLL()
