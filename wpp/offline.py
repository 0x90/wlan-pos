#!/usr/bin/env python
from __future__ import division
import os
import sys
import csv
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from time import strftime, ctime
import numpy as np
from pprint import pprint,PrettyPrinter

from wpp.config import DATPATH, RAWSUFFIX, RMPSUFFIX, CLUSTERKEYSIZE, \
        DB_OFFLINE, sqls, dbsvrs, mailcfg, errmsg, FTPCFG
from wpp.db import WppDB
from wpp.fingerprint import doClusterIncr, doClusterAll, genFPs
from wpp.util.net import getIP, sendMail


def usage():
    print """
offline.py - Copyleft 2009-%s Yan Xiaotian, xiaotian.yan@gmail.com.
Calibration & preprocessing for radio map generation in WLAN location fingerprinting.

usage:
    <sudo> offline <option> <infile>
option:
    -a --aio [NOT avail]   :  All-in-one offline processing.
    -c --cluster=<type id> :  Fingerprints clustering, type_id: 1-All,2-Incr.
    -d --db=<dbfiles>      :  Specify the db files to upload.
    -f --fake [for test]   :  Fake GPS scan results in case of bad GPS reception.
    -h --help              :  Show this help.
    -i --spid=<spid>       :  Sampling point id.
    -k --kml=<cfprints.tbl>:  Generate KML format from cfprints table file.
    -m --mode=<mode id>    :  Indicate the processing mode: 1-all; 2-incr.
    -n --no-dump           :  No data dumping to file.
    -r --rawdata=<rawfile> :  Load rawdata into WppDB, including algo related tables. 
                              1) db.initTables(); db.updateIndexes(); 2)doClusterIncr(),
                              under certain mode(specify with -m, default=all).
    -s --raw-scan=<times>  :  Scan for <times> times and log in raw file. 
    -t --to-rmp=<rawfile>  :  Process the given raw data to radio map. 
    -u --updatedb=<mode>   :  Update algo data with synced rawdata from remote FTP.
    -v --verbose           :  Verbose mode.
NOTE:
    <rawfile> needed by -t/--to-rmp option must NOT have empty line(s)!
""" % strftime('%Y')


def genKMLfile(cfpsfile):
    """
    Generating KML format file with data in cfps sql table file.
    format of cfps table file:
    cluster id, spid, lat, lon, keyrsss
    """
    from wpp.util.kml import genKML
    from wpp.config import icon_types
    cfpsin = csv.reader( open(cfpsfile,'r') )
    cfps = np.array([ cluster for cluster in cfpsin ])[:,:4]
    cfps = [ [[ c[2], c[3], c[1], 'cluster:%s, spid:%s'%(c[0],c[1]) ]] for c in cfps ]
    if verbose: pp.pprint(cfps)
    else: print cfps
    kfile = 'kml/ap.kml'
    #homedir = os.path.expanduser('~')
    for type in icon_types:
        icon_types[type][1] = os.getcwd() + icon_types[type][1]
    genKML(cfps, kmlfile=kfile, icons=icon_types)


def getRaw():
    """
    Collecting scanning results for WLAN & GPS.
    *return: rawdata=[ time, lat, lon, mac1|mac2, rss1|rss2 ]
    """
    from wpp.util.wlan import scanWLAN_RE
    from wpp.util.gps import getGPS
    #FIXME:exception handling
    if fake: rawdata = [ 39.9229416667, 116.472673167 ]
    else: rawdata = getGPS(); 
    timestamp = strftime('%Y%m%d-%H%M%S')
    rawdata.insert(0,timestamp)

    #FIXME:exception handling
    wlan = scanWLAN_RE()
    #wlan = [ [ '00:0B:6B:3C:75:34','-89' ] , [ '00:25:86:23:A4:48','-86' ] ]
    #wlan = [ [] ]
    # judging whether the number of scanned wlan APs more than 4 is for clustering.
    #if wlan and (len(wlan) >= CLUSTERKEYSIZE): num_fields = len(wlan[0])
    if wlan: num_fields = len(wlan[0])
    else: return rawdata

    # Raw data: time, lat, lon, mac1|mac2, rss1|rss2
    # aps: [ [mac1, mac2], [rss1, rss2] ]
    # aps_raw: [ mac1|mac2, rss1|rss2 ]
    if not num_fields == 0:
        aps = [ [ ap[i] for ap in wlan ] for i in range(num_fields) ]
        aps_raw = [ '|'.join(ap) for ap in aps ]
        rawdata.extend(aps_raw)

    return rawdata


def dumpCSV(csvfile, content):
    """
    Appendding csv-formed content line(s) into csvfile.
    """
    if not content: print 'dumpCSV: Null content!'; sys.exit(99)
    print 'Dumping data to %s' % csvfile
    csvout = csv.writer( open(csvfile,'a') )
    if not isinstance(content[0], list): content = [ content ]
    csvout.writerows(content)


def syncFtpUprecs(ftpcfg=None, ver_wpp=None):
    """
    ftpcfg: connection string.
    ver_wpp:  current wpp version of rawdata.
    vers_fpp: fpp rawdata versions needed for wpp.
    localbzs: local path(s) of rawdata bzip2(s).
    """
    from ftplib import FTP
    ftp = FTP()
    #ftp.set_debuglevel(1)
    try:
        print ftp.connect(host=ftpcfg['ip'],port=ftpcfg['port'],timeout=ftpcfg['timeout'])
    except:
        sys.exit("FTP Connection Failed: %s@%s:%s !" % (ftpcfg['user'],ftpcfg['ip'],ftpcfg['port']))
    print ftp.login(user=ftpcfg['user'],passwd=ftpcfg['passwd'])
    print ftp.cwd(ftpcfg['path'])
    files = ftp.nlst()
    # Naming rule of bzip2 file: FPP_RawData_<hostname>_<ver>.csv.bz2
    try:
        bz2s_latest = [ f for f in files if f.endswith('bz2') 
                and (f.split('_')[-1].split('.')[0]).isdigit()
                and int(f.split('_')[-1].split('.')[0])>ver_wpp ]
    except ValueError:
        sys.exit('\nERROR: Rawdata bz2 file name should be: \nFPP_RawData_<hostname>_<ver>.csv.bz2!')
    localbzs = []
    for bz2 in bz2s_latest:
        cmd = 'RETR %s' % bz2
        localbz = '%s/%s' % (ftpcfg['localdir'], bz2)
        fd_local = open(localbz, 'wb')
        ftp.retrbinary(cmd, fd_local.write)
        fd_local.close()
        localbzs.append(localbz)
    #ftp.set_debuglevel(0)
    print ftp.quit()
    vers_fpp = [ int(f.split('_')[-1].split('.')[0]) for f in bz2s_latest ]
    return (vers_fpp,localbzs)


def updateAlgoData():
    """
    Update data directly used by Algo in DB(wpp_clusterid, wpp_cfps).
    1) Retrieve latest incremental rawdata(csv) from remote FTP server(hosted by FPP).
    2) Decompress bzip2, import CSV into wpp_uprecsinfo with its ver_uprecs, Update ver_uprecs in wpp_uprecsver.
    3) Incr clustering inserted rawdata for direct algo use.
    """
    from bz2 import BZ2File
    dbips = DB_OFFLINE
    for svrip in dbips:
        dbsvr = dbsvrs[svrip]
        wppdb = WppDB(dsn=dbsvr['dsn'], dbtype=dbsvr['dbtype'])
        ver_wpp = wppdb.getRawdataVersion()
        # Sync rawdata into wpp_uprecsinfo from remote FTP server.
        print 'Probing rawdata version > [%s]' % ver_wpp
        vers_fpp,localbzs = syncFtpUprecs(FTPCFG, ver_wpp)
        if not vers_fpp: print 'Not found!'; continue
        else: print 'Found new vers: %s' % vers_fpp
        # Handle each bzip2 file.
        alerts = {'vers':[], 'details':''}
        tab_rd = 'wpp_uprecsinfo'
        for bzfile in localbzs:
            # Filter out the ver_uprecs info from the name of each bzip file.
            ver_bzfile = bzfile.split('_')[-1].split('.')[0]
            # Update ver_uprecs in wpp_uprecsver to ver_bzfile.
            wppdb.setRawdataVersion(ver_bzfile)
            print '%s\nUpdate ver_uprecs -> [%s]' % ('-'*40, ver_bzfile)
            # Decompress bzip2.
            sys.stdout.write('Decompress & append rawdata ... ')
            csvdat = csv.reader( BZ2File(bzfile) )
            try:
                indat = np.array([ line for line in csvdat ])
            except csv.Error, e:
                sys.exit('\n\nERROR: %s, line %d: %s!\n' % (bzfile, csvdat.line_num, e))
            # Append ver_uprecs info to last col.
            vers = np.array([ [ver_bzfile] for i in xrange(len(indat)) ])
            indat_withvers = np.append(indat, vers, axis=1).tolist(); print 'Done'
            # Import csv into wpp_uprecsinfo.
            try:
                sys.stdout.write('Import rawdata: ')
                wppdb.insertMany(table_name=tab_rd, indat=indat_withvers, verb=True)
            except Exception, e:
                _lineno = sys._getframe().f_lineno
                _file = sys._getframe().f_code.co_filename
                alerts['details'] += '\n[ver:%s][%s:%s]: %s' % \
                        (ver_bzfile, _file, _lineno, str(e).replace('\n', ' '))
                alerts['vers'].append(ver_bzfile)
                print 'ERROR: Insert Rawdata Failed!'
                continue
            # Incr clustering. 
            # file described by fd_csv contains all *location enabled* rawdata from wpp_uprecsinfo.
            strWhere = 'WHERE lat!=0 and lon!=0 and ver_uprecs=%s' % ver_bzfile
            cols_select = ','.join(wppdb.tbl_field[tab_rd][:-1])
            sql = wppdb.sqls['SQL_SELECT'] % ( cols_select, '%s %s'%(tab_rd,strWhere) )
            rdata_loc = wppdb.execute(sql=sql, fetch_one=False)
            if not rdata_loc: continue    # NO FPs has location info.
            str_rdata_loc = '\n'.join([ ','.join([str(col) for col in fp]) for fp in rdata_loc ])
            fd_csv = StringIO(str_rdata_loc)
            print 'FPs for Incr clustering selected & ready'
            n_inserts = doClusterIncr(fd_csv=fd_csv, wppdb=wppdb, verb=False)
            print 'AlgoData added: [%s] clusters, [%s] FPs' % (n_inserts['n_newcids'], n_inserts['n_newfps'])
        # Move rawdata without location to another table: wpp_uprecs_noloc.
        tab_rd_noloc = 'wpp_uprecs_noloc'
        strWhere = 'lat=0 or lon=0'
        sql = wppdb.sqls['SQL_INSERT_SELECT'] % ( tab_rd_noloc, '*', '%s WHERE %s'%(tab_rd,strWhere) )
        wppdb.cur.execute(sql)
        sql = wppdb.sqls['SQL_DELETE'] % (tab_rd, strWhere)
        wppdb.cur.execute(sql)
        wppdb.close()
        print 'Move noloc rawdata -> |%s|' % tab_rd_noloc
        if alerts['vers']:
            # Send alert email to admin.
            _func = sys._getframe().f_code.co_name
            subject = "[!]WPP ERROR: %s->%s, ver: [%s]" % (_file, _func, ','.join(alerts['vers']))
            body = ( errmsg['db'] % (tab_rd,'insert',alerts['details'],getIP()['eth0'],ctime()) ).decode('utf-8')
            print subject, body
            print 'Sending alert email -> %s' % mailcfg['to']
            sendMail(mailcfg['from'],mailcfg['userpwd'],mailcfg['to'],subject,body)

def loadRawdata(rawfile=None, updbmode=1):
    """
    rawfile: rawdata csv file.
    updbmode: update db mode: 1-all, 2-incr.

    Init *algo* tables with rawdata csv(16 columns) -- SLOW if csv is big, 
        try offline.doClusterAll(rawdata) -> db.loadClusteredData() instead.
    1) db.initTables(): init db tables.
    2) db.updateIndexes(): update tables indexes.
    3) offline.doClusterIncr(): incremental clustering.
    """
    dbips = DB_OFFLINE
    doflush = True
    for svrip in dbips:
        dbsvr = dbsvrs[svrip]
        wppdb = WppDB(dsn=dbsvr['dsn'], dbtype=dbsvr['dbtype'])
        if updbmode == 1:
            # Create WPP tables.
            wppdb.initTables(doDrop=True)
            doflush = False
        # Update indexs.
        wppdb.updateIndexes(doflush)
        # Load csv clustered data into DB tables.
        n_inserts = doClusterIncr(fd_csv=file(rawfile), wppdb=wppdb)
        print 'Added: [%s] clusters, [%s] FPs' % (n_inserts['n_newcids'], n_inserts['n_newfps'])
        # Init ver_uprecs in |wpp_uprecsver| if it's empty.
        if wppdb.getRawdataVersion() is None: wppdb.setRawdataVersion('0')
        wppdb.close()


def main():
    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ac:fhi:k:m:nr:s:t:uv",
            ["aio","cluster","fake","help","spid=","kml=","mode=","no-dump",
             "rawdata","raw-scan=","to-rmp=","updatedb","verbose"])
    except getopt.GetoptError:
        usage()
        sys.exit(99)

    if not opts: usage(); sys.exit(0)

    # global vars init.
    spid=0; times=0; tormp=False; updatedb=False; doLoadRawdata=False
    rawfile=None; tfail=0; docluster=False; dokml=False; updbmode=1
    global verbose,pp,nodump,fake
    verbose=False; pp=None; nodump=False; fake=False

    for o,a in opts:
        if o in ("-i", "--spid"):
            if a.isdigit(): spid = int(a)
            else:
                print '\nspid: %s should be an INTEGER!' % str(a)
                usage(); sys.exit(99)
        elif o in ("-m", "--mode"):
            if a.isdigit(): 
                updbmode = int(a)
                if not (1 <= updbmode <= 2):
                    print '\nError: updatedb mode: (%d) NOT supported yet!' % updbmode
                    usage(); sys.exit(99)
            else:
                print '\nmode: %s should be an INTEGER!' % str(a)
                usage(); sys.exit(99)
        elif o in ("-r", "--rawdata"):
            if not os.path.isfile(a):
                print 'Rawdata file NOT exist: %s' % a
                sys.exit(99)
            else: 
                doLoadRawdata = True
                rawfile = a
        elif o in ("-s", "--raw-scan"):
            if a.isdigit(): times = int(a)
            else: 
                print '\nError: "-s/--raw-scan" should be followed by an INTEGER!'
                usage(); sys.exit(99)
        elif o in ("-t", "--to-rmp"):
            if not os.path.isfile(a):
                print 'Raw data file NOT exist: %s' % a
                sys.exit(99)
            else: 
                tormp = True
                rawfile = a
        elif o in ("-c", "--cluster"):
            if not a.isdigit(): 
                print '\ncluster type: %s should be an INTEGER!' % str(a)
                usage(); sys.exit(99)
            else:
                # 1-All; 2-Incr.
                cluster_type = int(a)
                docluster = True
                rmpfile = sys.argv[3]
                if not os.path.isfile(rmpfile):
                    print 'Raw data file NOT exist: %s!' % rmpfile
                    sys.exit(99)
        elif o in ("-k", "--kml"):
            if not os.path.isfile(a):
                print 'cfprints table file NOT exist: %s' % a
                sys.exit(99)
            else: 
                dokml = True
                cfpsfile = a
        elif o in ("-n", "--no-dump"):
            nodump = True
        elif o in ("-f", "--fake"):
            fake = True
        elif o in ("-u", "--updatedb"):
            updatedb = True
        #elif o in ("-a", "--aio"):
        elif o in ("-v", "--verbose"):
            verbose = True
            pp = PrettyPrinter(indent=2)
        elif o in ("-h", "--help"):
            usage(); sys.exit(0)
        else:
            print 'Parameter NOT supported: %s' % o
            usage(); sys.exit(99)

    if doLoadRawdata:
        loadRawdata(rawfile, updbmode)

    # Update Algorithm related data.
    if updatedb:
        updateAlgoData()

    # Ordinary fingerprints clustering.
    if docluster:
        if cluster_type   == 1: 
            doClusterAll(file(rmpfile))
        elif cluster_type == 2: 
            dbips = DB_OFFLINE
            for svrip in dbips:
                dbsvr = dbsvrs[svrip]
                wppdb = WppDB(dsn=dbsvr['dsn'], dbtype=dbsvr['dbtype'])
                n_inserts = doClusterIncr(fd_csv=file(rmpfile), wppdb=wppdb)
                print 'Added: [%s] clusters, [%s] FPs' % (n_inserts['n_newcids'], n_inserts['n_newfps'])
                wppdb.close()
        else: sys.exit('Unsupported cluster type code: %s!' % cluster_type)

    # KML generation.
    if dokml:
        genKMLfile(cfpsfile)

    # Raw data to fingerprint convertion.
    if tormp:
        fingerprint = []
        fingerprint = genFPs(rawfile)
        if not fingerprint:
            print 'Error: Fingerprint generation FAILED: %s' % rawfile
            sys.exit(99)
        if nodump is False:
            if not rawfile == None: 
                date = strftime('%Y-%m%d')
                rmpfilename = DATPATH + date + RMPSUFFIX
                dumpCSV(rmpfilename, fingerprint)
                print '-'*65
                sys.exit(0)
            else:
                usage(); sys.exit(99)
        else:
            if verbose: pp.pprint(fingerprint)
            else: print fingerprint
            sys.exit(0)

    # WLAN & GPS scan for raw data collection.
    if not times == 0:
        for i in range(times):
            print "Survey: %d" % (i+1)
            rawdata = getRaw()
            rawdata.insert(0, spid)
            # Rawdata Integrity check,
            # Format: spid, time, lat, lon, mac1|mac2, rss1|rss2
            print rawdata
            if len(rawdata) == 6: 
                if verbose: 
                    pp.pprint(rawdata)
                else:
                    print 'Calibration at sampling point %d ... OK!' % spid
            else: 
                # wlan scanned APs less than CLUSTERKEYSIZE:4.
                tfail += 1
                print 'Time: %s\nError: Raw integrity check failed! Next!' % rawdata[1]
                print '-'*65
                continue
            # Raw data dumping to file.
            if nodump is False:
                if not os.path.isdir(DATPATH):
                    try:
                        os.umask(0) #linux system default umask: 022.
                        os.mkdir(DATPATH,0777)
                        #os.chmod(DATPATH,0777)
                    except OSError, errmsg:
                        print "Failed: %d" % str(errmsg)
                        sys.exit(99)
                date = strftime('%Y-%m%d')
                rfilename = DATPATH + date + ('-%06d' % spid) + RAWSUFFIX
                dumpCSV(rfilename, rawdata)
            print '-'*50
        #Scan Summary
        print '\nOK/Total:%28d/%d\n' % (times-tfail, times)


if __name__ == "__main__":
    main()
