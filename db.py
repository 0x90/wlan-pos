#!/usr/bin/env python
import sys
import os
import csv
import pprint
import StringIO as sio
import numpy as np
import cx_Oracle as ora
import psycopg2 as pg

from config import dbsvrs, tbl_names, tbl_field, tbl_forms, tbl_idx, tbl_files, \
        dsn_local_ora, dsn_vance_ora, dsn_local_pg, dsn_vance_pg_mic, dbtype_ora, dbtype_pg, sqls


class WppDB(object):
    def __init__(self,dsn=None,tbl_names=tbl_names,tbl_field=None,tbl_forms=None,sqls=None,
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
                if not e.pgcode or not e.pgerror: sys.exit('Connection failed!\n%s' % e)
                else: sys.exit('\nERROR: %s: %s\n' % (e.pgcode, e.pgerror))
        else: sys.exit('\nERROR: Unsupported DB type: %s!' % self.dbtype)

        if not tbl_field or not tbl_forms or not tbl_names:
            sys.exit('Need name, field, format definition for all tables!')
        self.tbl_names = tbl_names
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

    def getCIDcount(self, macs=None):
        if not macs: sys.exit('Need macs!')
        strWhere = "%s%s%s" % ("keyaps='", "' or keyaps='".join(macs), "'")
        sql = self.sqls['SQL_SELECT'] % ("clusterid, count(clusterid) cmask", 
                "wpp_clusteridaps where (%s) group by clusterid order by cmask desc"%strWhere)
        print sql
        self.cur.execute(sql)
        return self.cur.fetchall()

    def load_tables(self, tbl_files=None):
        if not self.tbl_files: 
            if not tbl_files:
                sys.exit('\nERROR: %s: Need a csv file!\n' % csvfile)
            else: self.tbl_files = tbl_files
        else: pass

        for table_name in self.tbl_names:
            table_inst = self.tbl_names[table_name]
            csvfile = self.tbl_files[table_name]
            if not os.path.isfile(csvfile):
                sys.exit('\n%s is NOT a file!' % (csvfile))
            #
            print 'TRUNCATE TABLE: %s' % table_inst
            self.cur.execute(self.sqls['SQL_TRUNCTB'] % table_inst)
            #
            #print 'DROP TABLE: %s' % table_inst
            #self.cur.execute(self.sqls['SQL_DROPTB'] % table_inst)
            #print 'CREATE TABLE: %s' % table_inst
            #self.cur.execute(self.sqls['SQL_CREATETB'] % \
            #        (table_inst, self.tbl_forms[table_name]))
            # Load the csv file.
            self._loadFile(csvfile=csvfile, table_inst=table_inst)
            # Update the number of records.
            self.cur.execute(self.sqls['SQL_SELECT'] % ('COUNT(*)', table_inst))
            print 'Total %s rows in %s now.' % (self.cur.fetchone()[0], table_inst)
            # Update indexs.
            if self.tbl_idx:
                for col_name in self.tbl_idx[table_name]:
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

    def _loadFile(self, csvfile=None, table_inst=None):
        if self.dbtype == 'oracle':
            # Import csv data.
            csvdat = csv.reader( open(csvfile,'r') )
            try:
                indat = [ line for line in csvdat ]
            except csv.Error, e:
                sys.exit('\nERROR: %s, line %d: %s!\n' % (csvfile, csvdat.line_num, e))
            self._insertMany(table_inst=table_inst, indat=indat)
        elif self.dbtype == 'postgresql':
            try:
                self.cur.copy_from(file(csvfile), table_inst, ',')
            except Exception, e:
                if not e.pgcode or not e.pgerror: sys.exit(e)
                else: sys.exit('\nERROR: %s: %s\n' % (e.pgcode, e.pgerror))
        else: sys.exit('\nERROR: Unsupported DB type: %s!' % self.dbtype)

    def _getNewCid(self, table_inst=None):
        sql = sqls['SQL_SELECT'] % ('max(clusterid)', table_inst)
        self.cur.execute(sql)
        cid = self.cur.fetchone()[0] + 1
        return cid

    def _insertMany(self, table_inst=None, indat=None):
        if self.dbtype == 'oracle':
            table_field = self.tbl_field[table_name]
            num_fields = len( table_field.split(',') )
            bindpos = '(%s)' % ','.join( ':%d'%(x+1) for x in xrange(num_fields) )
            self.cur.prepare(self.sqls['SQL_INSERT'] % (table_inst, table_field, bindpos))
            self.cur.executemany(None, indat)
            print 'Add %d rows to |%s|' % (self.cur.rowcount, table_inst)
        elif self.dbtype == 'postgresql':
            str_indat = '\n'.join([ ','.join([str(col) for col in fp]) for fp in indat ])
            file_indat = sio.StringIO(str_indat)
            try:
                self.cur.copy_from(file_indat, table_inst, ',')
            except Exception, e:
                if not e.pgcode or not e.pgerror: sys.exit(e)
                else: sys.exit('\nERROR: %s: %s\n' % (e.pgcode, e.pgerror))
            print 'Add %d rows to |%s|' % (len(indat), table_inst)
        else: sys.exit('\nERROR: Unsupported DB type: %s!' % self.dbtype)
        self.con.commit()

    def addCluster(self, macs=None):
        table_name = 'wpp_clusteridaps'
        table_inst = self.tbl_names[table_name]
        cid = self._getNewCid(table_inst=table_inst)
        cidmacseq = []
        for seq,mac in enumerate(macs):
            cidmacseq.append([ cid, mac, seq+1 ])
        self._insertMany(table_inst=table_inst, indat=cidmacseq)
        return cid

    def addFps(self, cid=None, fps=None):
        table_name = 'wpp_cfps'
        table_inst = self.tbl_names[table_name]
        cids = np.array([ [cid] for i in xrange(len(fps)) ])
        fps = np.array(fps)
        cidfps = np.append(cids, fps, axis=1).tolist()
        self._insertMany(table_inst=table_inst, indat=cidfps)

    def getCIDcntMaxSeq(self, macs=None):
        table_name = 'wpp_clusteridaps'
        table_inst = self.tbl_names[table_name]
        table_field = self.tbl_field[table_name]
        if not type(macs) is list: 
            macs = list(macs)
        num_macs = len(macs)
        if not num_macs:
            sys.exit('Null macs!')
        strWhere = "%s%s%s" % ("keyaps='", "' or keyaps='".join(macs), "'")
        if self.dbtype == 'oracle':
            sql1 = self.sqls['SQL_SELECT'] % \
                ("clusterid cid, count(clusterid) cidcnt", 
                 "%s where (%s) group by clusterid order by cidcnt desc) a, %s t \
                 where (cidcnt=%s) group by a.cid,a.cidcnt order by cidcnt desc" % \
                (table_inst, strWhere, table_inst))
        elif self.dbtype == 'postgresql':
            sql1 = self.sqls['SQL_SELECT'] % \
                ("clusterid as cid, count(clusterid) as cidcnt", 
                 "%s where (%s) group by clusterid order by cidcnt desc) a, %s t \
                 where (cidcnt=%s) group by cid,cidcnt order by cidcnt desc" % \
                (table_inst, strWhere, table_inst, num_macs))
        else: sys.exit('\nERROR: Unsupported DB type: %s!' % self.dbtype)
        sql = self.sqls['SQL_SELECT'] % ("cid,cidcnt,max(t.seq)", "(%s"%sql1)
        #print sql
        self.cur.execute(sql)
        return self.cur.fetchall()


if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=2)

    dbips = ('local_pg', )
    for svrip in dbips:
        dbsvr = dbsvrs[svrip]
        #print 'Loading data to DB svr: %s' % svrip
        print '%s %s %s' % ('='*15, svrip, '='*15)
        #tbl_names['wpp_clusteridaps']='wpp_clusteridaps_all'
        #tbl_names['wpp_cfps']='wpp_cfps_all'
        tbl_names['wpp_clusteridaps']='wpp_clusteridaps_incr'
        tbl_names['wpp_cfps']='wpp_cfps_incr'
        wppdb = WppDB(dsn=dbsvr['dsn'], dbtype=dbsvr['dbtype'], tbl_idx=tbl_idx, sqls=sqls, 
                tbl_names=tbl_names,tbl_field=tbl_field,tbl_forms=tbl_forms)
        wppdb.load_tables(tbl_files)
        wppdb.close()
