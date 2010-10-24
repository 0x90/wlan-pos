#!/usr/bin/env python
import sys
import os
import csv
import pprint
import cx_Oracle as ora
import psycopg2 as pg


tbl_field = { 'cidaps':'(cid, keyaps, seq)',
                'cfps':'(cid, lat, lon, h, rsss, cfps_time)',
              'tsttbl':'(cid, lat, lon)' }
tbl_idx =   { 'cidaps':['cid'], #{table_name:{'field_name'}}
                'cfps':['cid'],
              'tsttbl':['cid']}
tbl_files = { 'cidaps':'tbl/cidaps.tbl', 
                'cfps':'tbl/cfprints.tbl',
              'tsttbl':'tbl/tsttbl.tbl' }
# wpp_clusteridaps, wpp_cfps
tbl_forms = { 'oracle':{
                'cidaps':""" (  
                       cid INT, 
                    keyaps VARCHAR2(360),
                       seq INT)""", 
                'cfps':""" (  
                       cid INT,
                       lat NUMBER(9,6),
                       lon NUMBER(9,6),
                         h NUMBER(5,1),
                      rsss VARCHAR2(100),
                 cfps_time VARCHAR2(20))""",
                'tsttbl':"""(
                       cid INT, 
                       lat NUMBER(9,6), 
                       lon NUMBER(9,6))""" },
              'postgresql':{
                'cidaps':"""(
                       cid INT, 
                    keyaps VARCHAR(360),
                       seq INT)""", 
                'cfps':""" (  
                       cid INT,
                       lat NUMERIC(9,6),
                       lon NUMERIC(9,6),
                         h NUMERIC(5,1),
                      rsss VARCHAR(100),
                 cfps_time VARCHAR(20))""",
                'tsttbl':"""(
                       cid INT, 
                       lat NUMERIC(9,6), 
                       lon NUMERIC(9,6))""" }}
sqls = { 'SQL_SELECT' : "SELECT %s FROM %s",
         'SQL_DROPTB' : "DROP TABLE %s PURGE",
        'SQL_TRUNCTB' : "TRUNCATE TABLE %s",
       'SQL_CREATETB' : "CREATE TABLE %s %s",
      'SQL_CREATEIDX' : "CREATE INDEX %s ON %s(%s)",
     'SQL_CREATEUIDX' : "CREATE UNIQUE INDEX %s ON %s(%s)",
         'SQL_INSERT' : "INSERT INTO %s %s VALUES %s"}


class WppDB(object):
    def __init__(self,dsn=None,tbl_field=None,tbl_forms=None,sqls=None,
            tbl_files=None,tbl_idx=None,dbtype=None):
        if not dsn: sys.exit('Need DSN info!')
        if not dbtype: sys.exit('Need DB type!') 
        self.dbtype = dbtype
        if self.dbtype == 'oracle':
            try:
                self.con = ora.connect(dsn) #'yxt/yxt@localhost:1521/XE'
            except ora.DatabaseError, e:
                sys.exit('\nERR: %s' % e)
        elif self.dbtype == 'postgresql':
            try:
                self.con = pg.connect(dsn) #"host=localhost dbname=wppdb user=yxt password=yxt port=5433"
                self.con.set_isolation_level(pg.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            except Exception, e:
                sys.exit('\nERR: %d: %s\n' % (e.pgcode, e.pgerror))
        else: sys.exit('\nERR: Unsupported DB type: %s!' % self.dbtype)

        if not tbl_field or not tbl_forms:
            sys.exit('Need field, format definition for all tables!')
        self.tbl_field = tbl_field
        self.tbl_forms = tbl_forms
            
        if not sqls: sys.exit('Need sql set!')
        self.sqls = sqls

        self.tbl_files = tbl_files
        self.tbl_idx = tbl_idx

        self.cur = self.con.cursor()

    def close(self):
        self.cur.close()
        self.con.close()

    def load_tables(self, tbl_files=None):
        if not self.tbl_files: 
            if not tbl_files:
                sys.exit('\nERR: %s: Need a csv file!\n' % csvfile)
            else: self.tbl_files = tbl_files
        else: pass

        for table in self.tbl_field:
            csvfile = self.tbl_files[table]
            if not os.path.isfile(csvfile):
                sys.exit('\n%s is NOT a file!' % (csvfile))

            print 'TRUNCATE TABLE: %s' % table
            self.cur.execute(self.sqls['SQL_TRUNCTB'] % table)

            #print 'DROP TABLE: %s' % table
            #self.cur.execute(self.sqls['SQL_DROPTB'] % table)
            #print 'CREATE TABLE: %s' % table
            #self.cur.execute(self.sqls['SQL_CREATETB'] % \
            #        (table, self.tbl_forms[table]))
            if self.dbtype == 'oracle':
                # Import csv data.
                csvdat = csv.reader( open(csvfile,'r') )
                try:
                    indat = [ line for line in csvdat ]
                except csv.Error, e:
                    sys.exit('\nERR: %s, line %d: %s!\n' % (csvfile, csvdat.line_num, e))
                print 'csv data %d records.' % len(indat)

                # make position binding like (1,2,3).
                #num_fields = len( self.tbl_field[table].split(',') )
                #bindpos = '(%s)' % ','.join( ':%d'%(x+1) for x in xrange(num_fields) )
                #self.cur.prepare(self.sqls['SQL_INSERT'] % \
                #        (table, self.tbl_field[table], bindpos))
                #self.cur.executemany(None, indat)
                #print 'Inserted %d rows.' % self.cur.rowcount
            elif self.dbtype == 'postgresql':
                self.cur.copy_from(file(csvfile), table, ',')
            else: sys.exit('\nERR: Unsupported DB type: %s!' % self.dbtype)

            self.cur.execute(self.sqls['SQL_SELECT'] % ('COUNT(*)', table))
            print 'Total %s rows in %s now.' % (self.cur.fetchone()[0], table)
            #if self.tbl_idx:
            #    for col_name in self.tbl_idx[table]:
            #        # index naming rule: i_tablename_colname.
            #        idx_name = 'i_%s_%s' % (table, col_name)
            #        self.cur.execute(self.sqls['SQL_CREATEIDX'] % \
            #                (idx_name, table, col_name))
            #        print self.sqls['SQL_CREATEIDX'] % (idx_name,table,col_name)
            print '-'*40

        self.con.commit()


    # Unfortunately, load is NOT a known cmd for oracle.
    #print SQL_CSVIN % ('orain.dat', 'tsttbl', tbl_forms['tsttbl'])
    #cur.execute(SQL_CSVIN % ('orain', 'tsttbl', tbl_field['tsttbl']))


if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=2)

    dsn_local_ora = "yxt/yxt@localhost:1521/XE"
    dsn_vance_ora = "mwlan/mwlan_pw@192.168.35.202/wlandb"
    dsn_local_pg = "host=localhost dbname=wppdb user=yxt password=yxt port=5433"
    dbtype_ora = 'oracle'; dbtype_pg = 'postgresql'

    wppdb = WppDB(dsn=dsn_local_pg, dbtype=dbtype_pg, tbl_idx=tbl_idx, 
            tbl_field=tbl_field, tbl_forms=tbl_forms['postgresql'], sqls=sqls)
    wppdb.load_tables(tbl_files)
    wppdb.close()
