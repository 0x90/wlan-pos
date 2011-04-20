#!/usr/bin/env python
import sys
import os
import csv
import pprint
import StringIO as sio
import numpy as np
#import cx_Oracle as ora
import psycopg2 as pg

from config import dbsvrs, wpp_tables, sqls, DB_UPLOAD, \
        tbl_field, tbl_forms, tbl_idx, tbl_files, \
        dsn_local_ora, dsn_vance_ora, dsn_local_pg, dsn_vance_pg_mic, dbtype_ora, dbtype_pg


def usage():
    import time
    print """
db.py - Copyleft 2009-%s Yan Xiaotian, xiaotian.yan@gmail.com.
Abstraction layer for WPP radiomap DB handling.

usage:
    db <option> 
option:
    normal:  wpp_clusteridaps & wpp_cfps.
    call  :  All-clustering table import.
    cincr :  Incr-clustering table import.
    uprec :  uprecs rawdata table import.
example:
    #db.py normal
""" % time.strftime('%Y')


class WppDB(object):
    def __init__(self,dsn=None,tables=wpp_tables,tbl_field=None,tbl_forms=None,sqls=None,
            tbl_files=None,tbl_idx=None,dbtype=None):
        if not dsn: sys.exit('Need DSN info!')
        if not dbtype: sys.exit('Need DB type!') 
        self.dbtype = dbtype
        if self.dbtype == 'oracle':
            try:
                self.con = ora.connect(dsn) #'yxt/yxt@localhost:1521/XE'
            except ora.DatabaseError, e:
                sys.exit('\nERROR: %s' % e)
        elif self.dbtype == 'postgresql':
            try:
                self.con = pg.connect(dsn) 
                self.con.set_isolation_level(pg.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            except Exception, e:
                if not e.pgcode or not e.pgerror: sys.exit('PostgreSQL: Connection failed!\n%s' % e)
                else: sys.exit('\nERROR: %s: %s\n' % (e.pgcode, e.pgerror))
        else: sys.exit('\nERROR: Unsupported DB type: %s!' % self.dbtype)

        if not tbl_field or not tbl_forms or not tables:
            sys.exit('Need name, field, format definition for all tables!')
        self.tables = wpp_tables
        self.tbl_field = tbl_field
        self.tbl_forms = tbl_forms[self.dbtype]
            
        if not sqls: sys.exit('Need sql set!')
        self.sqls = sqls

        self.tbl_files = tbl_files
        self.tbl_idx = tbl_idx

        self.cur = self.con.cursor()

    def close(self):
        self.cur.close()
        self.con.close()

    def loadTables(self, tbl_files=None):
        if not self.tbl_files: 
            if not tbl_files:
                sys.exit('\nERROR: %s: Need a csv file!\n' % csvfile)
            else: self.tbl_files = tbl_files
        else: pass

        for table_name in self.tables:
            table_inst = self.tables[table_name]
            csvfile = self.tbl_files[table_name]
            if not os.path.isfile(csvfile):
                sys.exit('\n%s is NOT a file!' % (csvfile))
            #
            #print 'TRUNCATE TABLE: %s' % table_inst
            #self.cur.execute(self.sqls['SQL_TRUNCTB'] % table_inst)
            #
            #print 'DROP TABLE: %s' % table_inst
            #self.cur.execute(self.sqls['SQL_DROPTB'] % table_inst)
            print 'CREATE TABLE: %s' % table_inst
            self.cur.execute(self.sqls['SQL_CREATETB'] % \
                    (table_inst, self.tbl_forms[table_name]))
            # Load the csv file.
            self._loadFile(csvfile=csvfile, table_name=table_name)
            # Update the number of records.
            self.cur.execute(self.sqls['SQL_SELECT'] % ('COUNT(*)', table_inst))
            print 'Total [%s] rows in |%s|' % (self.cur.fetchone()[0], table_inst)
            # Update indexs.
            if self.tbl_idx:
                for col_name in self.tbl_idx[table_name]:
                    if not col_name: continue
                    # index naming rule: i_tablename_colname.
                    idx_name = 'i_%s_%s' % (table_inst, col_name)
                    # drop indexs.
                    if self.dbtype == 'oracle':
                        sql_drop_idx = self.sqls['SQL_DROP_IDX'] % idx_name
                    elif self.dbtype == 'postgresql':
                        sql_drop_idx = self.sqls['SQL_DROP_IDX_IE'] % idx_name
                    else: sys.exit('\nERROR: Unsupported DB type: %s!' % self.dbtype)
                    self.cur.execute(sql_drop_idx)
                    print sql_drop_idx
                    # create indexs.
                    sql_make_idx = self.sqls['SQL_CREATEIDX'] % (idx_name,table_inst,col_name)
                    self.cur.execute(sql_make_idx)
                    print sql_make_idx
            print '-'*40

        self.con.commit()

    def _loadFile(self, csvfile=None, table_name=None):
        if self.dbtype == 'oracle':
            # Import csv data.
            csvdat = csv.reader( open(csvfile,'r') )
            try:
                indat = [ line for line in csvdat ]
            except csv.Error, e:
                sys.exit('\nERROR: %s, line %d: %s!\n' % (csvfile, csvdat.line_num, e))
            self._insertMany(table_name=table_name, indat=indat)
        elif self.dbtype == 'postgresql':
            if not table_name == 'wpp_uprecsinfo': cols = None
            else: cols = self.tbl_field[table_name]
            table_inst = self.tables[table_name]
            try:
                self.cur.copy_from(file(csvfile), table_inst, sep=',', columns=cols)
            except Exception, e:
                if not e.pgcode or not e.pgerror: sys.exit(e)
                else: sys.exit('\nERROR: %s: %s\n' % (e.pgcode, e.pgerror))
        else: sys.exit('\nERROR: Unsupported DB type: %s!' % self.dbtype)

    def _getNewCid(self, table_inst=None):
        sql = sqls['SQL_SELECT'] % ('max(clusterid)', table_inst)
        self.cur.execute(sql)
        new_cid = self.cur.fetchone()[0] + 1
        return new_cid

    def _insertMany(self, table_name=None, indat=None):
        table_inst = self.tables[table_name]
        if self.dbtype == 'oracle':
            table_field = self.tbl_field[table_name]
            num_fields = len(table_field)
            bindpos = '(%s)' % ','.join( ':%d'%(x+1) for x in xrange(num_fields) )
            self.cur.prepare(self.sqls['SQL_INSERT'] % \
                    (table_inst, '(%s)'%(','.join(table_field)), bindpos))
            self.cur.executemany(None, indat)
            print 'Add %d rows to |%s|' % (self.cur.rowcount, table_inst)
        elif self.dbtype == 'postgresql':
            str_indat = '\n'.join([ ','.join([str(col) for col in fp]) for fp in indat ])
            file_indat = sio.StringIO(str_indat)
            if not table_name == 'wpp_uprecsinfo': cols = None
            else: cols = self.tbl_field[table_name]
            try:
                self.cur.copy_from(file_indat, table_inst, sep=',', columns=cols)
            except Exception, e:
                if not e.pgcode or not e.pgerror: sys.exit(e)
                else: sys.exit('\nERROR: %s: %s\n' % (e.pgcode, e.pgerror))
            print 'Add %d rows to |%s|' % (len(indat), table_inst)
        else: sys.exit('\nERROR: Unsupported DB type: %s!' % self.dbtype)
        self.con.commit()

    def addCluster(self, macs=None):
        table_name = 'wpp_clusteridaps'
        table_inst = self.tables[table_name]
        new_cid = self._getNewCid(table_inst=table_inst)
        cidmacseq = []
        for seq,mac in enumerate(macs):
            cidmacseq.append([ new_cid, mac, seq+1 ])
        self._insertMany(table_name=table_name, indat=cidmacseq)
        return new_cid

    def addFps(self, cid=None, fps=None):
        table_name = 'wpp_cfps'
        cids = np.array([ [cid] for i in xrange(len(fps)) ])
        fps = np.array(fps)
        cidfps = np.append(cids, fps, axis=1).tolist()
        self._insertMany(table_name=table_name, indat=cidfps)

    def getCIDcntMaxSeq(self, macs=None):
        table_name = 'wpp_clusteridaps'
        table_inst = self.tables[table_name]
        if not type(macs) is list: macs = list(macs)
        num_macs = len(macs)
        if not num_macs: sys.exit('Null macs!')
        strWhere = "%s%s%s" % ("keyaps='", "' or keyaps='".join(macs), "'")
        if self.dbtype == 'oracle':
            sql1 = self.sqls['SQL_SELECT'] % \
                ("clusterid cid, count(clusterid) cidcnt", 
                 "%s where (%s) group by clusterid order by cidcnt desc) a, %s t \
                 where (a.cid=t.clusterid and a.cidcnt=%s) group by a.cid,a.cidcnt order by cidcnt desc" % \
                (table_inst, strWhere, table_inst))
        elif self.dbtype == 'postgresql':
            sql1 = self.sqls['SQL_SELECT'] % \
                ("clusterid as cid, count(clusterid) as cidcnt", 
                 "%s where (%s) group by clusterid order by cidcnt desc) a, %s t \
                 where (cid=clusterid and cidcnt=%s) group by cid,cidcnt order by cidcnt desc" % \
                (table_inst, strWhere, table_inst, num_macs))
        else: sys.exit('\nERROR: Unsupported DB type: %s!' % self.dbtype)
        sql = self.sqls['SQL_SELECT'] % ("cid,cidcnt,max(t.seq)", "(%s"%sql1)
        #print sql
        self.cur.execute(sql)
        return self.cur.fetchall()

    #maxNI,keys = [2, [
    #    [['00:21:91:1D:C0:D4', '00:19:E0:E1:76:A4', '00:25:86:4D:B4:C4'],
    #        [[5634, 5634, 39.898019, 116.367113, '-83|-85|-89']] ],
    #    [['00:21:91:1D:C0:D4', '00:25:86:4D:B4:C4'],
    #        [[6161, 6161, 39.898307, 116.367233, '-90|-90']] ] ]]
    def getBestClusters(self, macs=None):
        if not type(macs) is list: macs = list(macs)
        num_macs = len(macs)
        if not num_macs: sys.exit('Null macs!')
        # fetch id(s) of best cluster(s).
        cidcnt = self._getBestCIDMaxNI(macs)
        if not cidcnt.any(): return [0,None]
        maxNI = cidcnt[0,1]
        idx_maxNI = cidcnt[:,1].tolist().count(maxNI)
        best_clusters = cidcnt[:idx_maxNI,0]
        #print best_clusters
        cfps = self._getFPs(cids=best_clusters)
        #print cfps
        aps = self._getKeyMACs(cids=best_clusters)
        #print aps
        cids = aps[:,0].tolist()
        keys = []
        for i,cid in enumerate(best_clusters):
            keyaps  = [ x[1] for x in aps if x[0]==str(cid) ]
            keycfps = [ x for x in cfps if x[0]==cid ]
            keys.append([keyaps, keycfps])
        #print keys
        return [maxNI, keys]


    def _getKeyMACs(self, cids=None):
        table_name = 'wpp_clusteridaps'
        table_inst = self.tables[table_name]
        bc = [ str(x) for x in cids ]
        strWhere = "%s%s" % ("clusterid=", " or clusterid=".join(bc))
        #strWhere = "%s%s%s" % ("clusterid='", "' or clusterid='".join(bc), "'")
        sql = "SELECT * FROM %s WHERE (%s)" % (table_inst, strWhere)
        #print sql
        self.cur.execute(sql)
        return np.array(self.cur.fetchall())


    def _getFPs(self, cids=None):
        table_name = 'wpp_cfps'
        table_inst = self.tables[table_name]
        bc = [ str(x) for x in cids ]
        #strWhere = "%s%s%s" % ("clusterid='", "' or clusterid='".join(bc), "'")
        strWhere = "%s%s" % ("clusterid=", " or clusterid=".join(bc))
        sql = "SELECT * FROM %s WHERE (%s)" % (table_inst, strWhere)
        #print sql
        self.cur.execute(sql)
        return np.array(self.cur.fetchall())


    def _getBestCIDMaxNI(self, macs=None):
        table_name = 'wpp_clusteridaps'
        table_inst = self.tables[table_name]
        strWhere = "%s%s%s" % ("keyaps='", "' or keyaps='".join(macs), "'")
        if self.dbtype == 'postgresql':
            #sql = "SELECT cid,MAX(cidcnt) FROM (\
            #       SELECT clusterid AS cid, COUNT(clusterid) AS cidcnt \
            #       FROM %s WHERE (%s) GROUP BY cid) a,%s \
            #       WHERE cidcnt = (\
            #       SELECT MAX(cidcnt) as maxcidcnt FROM (\
            #       SELECT clusterid AS cid, COUNT(clusterid) AS cidcnt \
            #       FROM %s WHERE (%s) GROUP BY cid) b ) GROUP BY cid" % \
            #    (table_inst, strWhere, table_inst, table_inst, strWhere)
            sql = "SELECT clusterid AS cid, COUNT(clusterid) AS cidcnt \
                   FROM %s WHERE (%s) GROUP BY cid ORDER BY cidcnt desc" % \
                (table_inst, strWhere)
        elif self.dbtype == 'oracle':
            sql1 = self.sqls['SQL_SELECT'] % \
                ("clusterid cid, count(clusterid) cidcnt", 
                 "%s where (%s) group by clusterid order by cidcnt desc) a, %s t \
                 where (a.cid=t.clusterid and a.cidcnt=%s) group by a.cid,a.cidcnt order by cidcnt desc" % \
                (table_inst, strWhere, table_inst))
        else: sys.exit('\nERROR: Unsupported DB type: %s!' % self.dbtype)
        #print sql
        self.cur.execute(sql)
        return np.array(self.cur.fetchall())


if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=2)

    if sys.argv[1]:
        updb_opt = sys.argv[1]
        if updb_opt == 'call':
            wpp_tables['wpp_clusteridaps']='wpp_clusteridaps_all'
            wpp_tables['wpp_cfps']='wpp_cfps_all'
        elif updb_opt == 'cincr':
            wpp_tables['wpp_clusteridaps']='wpp_clusteridaps_incr'
            wpp_tables['wpp_cfps']='wpp_cfps_incr'
        elif updb_opt == 'uprec':
            wpp_tables['wpp_uprecsinfo']='wpp_uprecsinfo'
        elif updb_opt == 'normal':
            # ONLY load two algo tables: wpp_clusteridaps, wpp_cfps.
            pass
        else:
            print 'Unsupported db upload option: %s!' % updb_opt
            usage()
            sys.exit(0)
    else:
        print 'Unsupported db upload option: %s!' % updb_opt
        usage()
        sys.exit(0)

    #dbips = ('local_pg', )
    dbips = DB_UPLOAD
    #dbips = ('192.168.109.54', )
    for svrip in dbips:
        dbsvr = dbsvrs[svrip]
        #print 'Loading data to DB svr: %s' % svrip
        print '%s %s %s' % ('='*15, svrip, '='*15)
        wppdb = WppDB(dsn=dbsvr['dsn'],dbtype=dbsvr['dbtype'],tbl_idx=tbl_idx, 
                tables=wpp_tables,tbl_field=tbl_field,tbl_forms=tbl_forms,sqls=sqls)
        wppdb.loadTables(tbl_files)
        wppdb.close()
