#!/usr/bin/env python
#coding=utf-8
#Parse GPS info by listening NMEA0183 GPGLL sentence from serial port.
from __future__ import division
import serial,string
from time import sleep,strftime

def getGPS():
    """
    Bluez likes to use /dev/rfcomm0, but pyserial uses /dev/ttyS*.
    So be noticed to redirect rfcomm0 to ttyS* with following cmds:
    sudo rm /dev/ttyS0 -f && ln -s /dev/rfcomm0 /dev/ttyS0.
    """
    ser = serial.Serial()
    ser.port = 0; ser.baudrate = 4800
    ser.open()

    while True:
        line = ser.readline()
        sentence = line.split(',')

        """
        $GPGLL,3955.36937,N,11628.37507,E,011217.000,A,A*55
        $GPGGA,011217.000,3955.36937,N,11628.37507,E,1,04,4.0,41.3,M,-7.9,M,,*75
        $GPRMC,011217.000,A,3955.36937,N,11628.37507,E,,,271209,,,A*6D
        """
        if line.startswith('$GPGLL,'):
            if not len(sentence) == 8: continue
            try:
                # Format of sentence[5](utc): hhmmss
                #time = string.atof(sentence[5])
                lat_tmp = string.atof(sentence[1])
                lon_tmp = string.atof(sentence[3])
            except: 
                continue

        elif line.startswith('$GPGGA,'):
            if not len(sentence) == 15: continue
            try:
                #time = string.atof(sentence[1])
                lat_tmp = string.atof(sentence[2])
                lon_tmp = string.atof(sentence[4])
            except: 
                continue

        #elif line.startswith('$GPRMC,'):
        #    if not len(sentence) == 13: continue
        #    try:
        #        #time = string.atof(sentence[1])
        #        lat_tmp = string.atof(sentence[3])
        #        lon_tmp = string.atof(sentence[5])
        #    except:
        #        continue
        else:
            continue

        print '-'*60
        print line

        #time: utc field of GLL,GGA,RMC sentence.
        #hour = int(time/10000)
        #min = int(time/100)-hour*100
        #sec = int(time)-hour*10000-min*100

        lat_int = int(lat_tmp/100)
        lat = lat_int + (lat_tmp - lat_int*100)/60
        lon_int = int(lon_tmp/100)
        lon = lon_int + (lon_tmp - lon_int*100)/60

        time = strftime('%Y%m%d-%H%M%S')

        gps = [ time, lon, lat ]
        break

    #sleep(.2)
    ser.close()
    return gps

if __name__ == "__main__":
    from pprint import pprint
    pprint(getGPS())
