#!/usr/bin/env python
import sys,os,re
from subprocess import Popen, STDOUT, PIPE, call
#from numpy import array, savetxt, dtype

_re_mode = (re.I | re.M | re.S)
patt_mac = re.compile('Address:\s*(.*?)\s*$', _re_mode)
#FIXME
#patt_mac = re.compile('.*Address: (([0-9A-Z]{2}:){5}[0-9A-Z]{2})', _re_mode)
patt_rss = re.compile('Signal level=?:? ?(-\d\d*) ?dBm', _re_mode)
# mac,essid,signal,noise,encryption
patt_all = re.compile('Address: ?(.*?)\n\
        .*ESSID: ?"?(.*?)"? *\n\
        .*Signal level=?:? ?(-\d\d*) ?dBm *Noise level ?=? ?(-\d\d*) ?dBm *\n\
        .*Encryption key:?=? ?(\w*) *\n', _re_mode)
# mac,rss
patt_rmap = re.compile('Address: ?(.*?)\n\
        .*Signal level=?:? ?(-\d\d*) *dBm', _re_mode)


def Run(cmd, include_stderr=False, return_pipe=False,
        return_obj=False, return_retcode=True):
    tmpenv = os.environ.copy()
    tmpenv["LC_ALL"] = "C"
    tmpenv["LANG"] = "C"
    try:
        fp = Popen(cmd, shell=False, stdout=PIPE, stdin=None, stderr=None,
                  close_fds=False, cwd='/', env=tmpenv)
    except OSError, e:
        print "Running command %s failed: %s" % (str(cmd), str(e))
        return ""
    return fp.communicate()[0]


def scanWLAN( cmd='sudo iwlist wlan0 scan'.split() ):
    """
    *return: [ [mac1, rss1], [mac2, rss2] ]
    """
    results = Run(cmd)
    networks = results.split( 'Cell' )
    scan_result = []
    for cell in networks:
        #TODO:exception handling.
        #found = patt_rmap.findall(cell) 
        matched = patt_rmap.search(cell) 

        # For re.findall's result - list
        #if isinstance(matched, list):
        #    scan_result = matched 

        # For re.search's result - either MatchObject or None,
        # and only the former has the attribute 'group(s)'.
        if matched is not None:
            # groups - all matched results corresponding to '()' 
            # field in the argument of re.compile().
            # group(0/1/2) - the whole section matched the expression/
            # the 1st/2nd matched field.
            # group() = group(0)
            found = list(matched.groups())

            # Move the 'essid' field to the end of 'found' list.
            # 2: found at least has mac,rss,essid.
            if len(found) > 2:
                found.append(found[1])
                found.pop(1)

            scan_result.append(found)
        else:
            continue

    return scan_result

if __name__ == "__main__":
    wlan = scanWLAN()
    #dt = dtype([
    #        ('mac','S17'),
    #        ('signal','i4'),
    #        ('noise','i4'),
    #        ('key','S3'),
    #        ('essid','S10')])
    #ary_wlan = array(wlan)
    #dt_wlan = array(ary_wlan[:,0],dtype=dt)
    #dt_wlan['signal'],dt_wlan['noise'],dt_wlan['key'],dt_wlan['essid'] = \
    #    ary_wlan[:,1], ary_wlan[:,2], ary_wlan[:,3], ary_wlan[:,4]

    from pprint import pprint
    pprint(wlan)

    #import csv
    #wlancsv = csv.writer( open('out.csv','wb'), delimiter='|' )
    #wlancsv.writerows(wlan)

    #savetxt("out", wlan, fmt='%s,%s,%s,%s,%s')
    #sys.exit(0)
