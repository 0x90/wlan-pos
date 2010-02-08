#!/usr/bin/env python
import struct,array,errno,fcntl,socket,time
import re#,os#,sys
from subprocess import Popen, PIPE


_re_mode = (re.I | re.M | re.S)
pmodes = {
        1: #patt_rss: mac,rss
        'Address: ?(.*?)\n\
        .*Signal level=?:? ?(-\d\d*) *dBm',
        2: #patt_all: mac,essid,signal,noise,encryption
        'Address: ?(.*?)\n\
        .*ESSID: ?"?(.*?)"? *\n\
        .*Signal level=?:? ?(-\d\d*) ?dBm *Noise level ?=? ?(-\d\d*) ?dBm *\n\
        .*Encryption key:?=? ?(\w*) *\n',
        #FIXME
        #'.*Address: (([0-9A-Z]{2}:){5}[0-9A-Z]{2})'
}


def Run(cmd, include_stderr=False, return_pipe=False,
        return_obj=False, return_retcode=True):
    #tmpenv = os.environ.copy()
    #tmpenv["LC_ALL"] = "C"
    #tmpenv["LANG"] = "C"
    try:
        fp = Popen(cmd, shell=False, stdout=PIPE, stdin=None, stderr=None,
                  close_fds=False, cwd='/')#, env=tmpenv)
    except OSError, e:
        print "Running command %s failed: %s" % (str(cmd), str(e))
        return ""
    return fp.communicate()[0]


def scanWLAN_RE(pmode=1):
    """
    *return: [ [mac1, rss1], [mac2, rss2], ... ]
    """

    cmd = 'sudo iwlist wlan0 scan'.split()
    results = Run(cmd)
    networks = results.split( 'Cell' )
    scan_result = []
    for cell in networks:
        #TODO:exception handling.
        #found = patt_rmap.findall(cell) 
        matched = re.compile(pmodes[pmode], _re_mode).search(cell) 
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
        else: continue
    return scan_result


def pack_wrq(buffsize):
    """ Packs wireless request data for sending it to the kernel. """
    # Prepare a buffer
    # We need the address of our buffer and the size for it. The
    # ioctl itself looks for the pointer to the address in our
    # memory and the size of it.
    # Don't change the order how the structure is packed!!!
    buff = array.array('c', '\0'*buffsize)
    caddr_t, length = buff.buffer_info()
    datastr = struct.pack('Pi', caddr_t, length)
    return buff, datastr


def _fcntl(request, args):
    sockfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return fcntl.ioctl(sockfd.fileno(), request, args)


def syscall(ifname, request, data=None):
    """ Read information from ifname. """
    buff = 16 - len(ifname)
    ifreq = array.array('c', ifname + '\0'*buff)
    # put some additional data behind the interface name
    if data is not None:
        ifreq.extend(data)
    else:
        buff = 32 # - pythonwifi.flags.IFNAMSIZE
        ifreq.extend('\0'*buff)

    result = _fcntl(request, ifreq)
    return (result, ifreq[16:])


def parse_qual(fmt, data):
    """ return ONLY qual, siglevel. """
    value = struct.unpack(fmt, data[0:2])

    # take care of a tuple like (int, )
    if len(value) == 1: return value[0]
    else: return value


def parse_all(data):
    # Run through the stream until it is too short to contain a command
    aplist = []
    while (len(data) >= 4):
        # Unpack the header
        length, cmd = struct.unpack('HH', data[:4])
        #print'length:%d, cmd: %x' % (length, cmd)
        # If the event length is too short to contain valid data,
        # then break, because we're probably at the end of the cell's data
        if length < 4: break;
        # Put the events into their respective result data
        if cmd == 0x8B15:
            #print 'AP found!'
            #if len(aplist) == 0: aplist.append([])
            bssid = "%02X:%02X:%02X:%02X:%02X:%02X" % \
                    ( struct.unpack('6B', data[4:length][2:8]) )
        elif cmd == 0x8c01:
            rss = struct.unpack("B", data[5:6])[0] - 256
            aplist.append([bssid, rss])
        data = data[length:]
    return aplist


def scanWLAN_OS():
    datastr = struct.pack("Pii", 0, 0, 0)
    status, result = syscall('wlan0', 0x8B18, datastr)

    repack = False
    bufflen = 4096
    buff, datastr = pack_wrq(bufflen)
    while (True):
        if repack is True:
            buff, datastr = pack_wrq(bufflen)
        try:
            status, result = syscall('wlan0', 0x8B19, data=datastr)
        except IOError, (error_number, error_string):
            if error_number == errno.E2BIG:
                #print 'E2BIG: %d' % errno.E2BIG
                # Keep resizing the buffer until it's
                #   large enough to hold the scan
                pbuff, newlen = struct.unpack('Pi', datastr)
                if bufflen < newlen:
                    # the driver told us how big to make the buffer
                    bufflen = newlen
                else:
                    # try doubling the buffer size
                    bufflen = bufflen * 2
                repack = True
            elif error_number == errno.EAGAIN: #try again.
                # Permission was NOT denied,
                #   therefore we must WAIT to get results
                time.sleep(0.1)
            else:
                raise
        except:
            raise
        else:
            break

    # unpack the buffer pointer and length
    pbuff, reslen = struct.unpack('Pi', datastr)
    if reslen > 0:
        aplist = parse_all(buff.tostring())
    return aplist


if __name__ == "__main__":
    #wlan_re = scanWLAN_RE(pmode=2)
    #time.sleep(2)
    wlan_os = scanWLAN_OS()

    from pprint import pprint
    #print 'visible APs: %d' % len(wlan_re)
    #pprint(wlan_re)
    print 'visible APs: %d' % len(wlan_os)
    pprint(wlan_os)

