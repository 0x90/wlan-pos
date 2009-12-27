#!/usr/bin/env python
import sys,os,re
from subprocess import Popen, STDOUT, PIPE, call

_re_mode = (re.I | re.M | re.S)
patt_mac = re.compile('Address:\s*(.*?)\s*$', _re_mode)
#FIXME
#patt_mac = re.compile('.*Address: (([0-9A-Z]{2}:){5}[0-9A-Z]{2})', _re_mode)
patt_sig = re.compile('Signal level=?:? ?(-\d\d*) ?dBm', _re_mode)
#mac,essid,signal,noise,encryption
patt_all = re.compile('Address: ?(.*?)\n\
        .*ESSID: ?"?(.*?)"? *\n\
        .*Signal level=?:? ?(-\d\d*) ?dBm *Noise level ?=? ?(-\d\d*) ?dBm *\n\
        .*Encryption key:?=? ?(\w*) *\n', _re_mode)
#mac,signal,noise
patt_rmap = re.compile('Address: ?(.*?)\n\
        .*Signal level=?:? ?(-\d\d*) ?dBm *Noise level ?=? ?(-\d\d*) ?dBm *', _re_mode)


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
    result = Run(cmd)
    networks = result.split( 'Cell' )
    mac_rssi = []
    for cell in networks:
        #TODO:exception handling.
        #found = patt_rmap.findall(cell) 
        matched = patt_all.search(cell) 

        # For re.findall's result - list
        #if isinstance(matched, list):
        #    mac_rssi = matched 

        # For re.search's result - either MatchObject or None,
        # and only the former has the attribute 'group(s)'.
        if matched is not None:
            # groups - all matched results corresponding to '()' 
            # field in the argument of re.compile().
            # group(0/1/2) - the whole section matched the expression/
            # the 1st/2nd matched field.
            # group() = group(0)
            found = list(matched.groups())

            #Move the 'essid' field to the end of 'found' list.
            if len(found) > 1:
                found.append(found[1])
                found.pop(1)

            mac_rssi.append(found)
        else:
            continue

    return mac_rssi

if __name__ == "__main__":
    from pprint import pprint
    pprint(scanWLAN())
