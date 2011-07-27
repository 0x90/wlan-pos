#!/usr/bin/env python
# dump data from sqlite3 db cell_area.db to pg db wpp_cellarea.
import sqlite3 as sl
import psycopg2 as pg

db_old = sl.connect('cell_area.db')
db_new = pg.connect("host=localhost dbname=wppdb user=wpp password=wpp port=5432")

cur_old = db_old.cursor()
cur_new = db_new.cursor()

cur_old.execute('select * from cell_area')
data_old = cur_old.fetchall()

print len(data_old)

for line in data_old:
    cellid, acode, aname, lac = line
    laccid = '%s-%s' % (lac, cellid)
    aname = "\\'".join(aname.split("'"))
    aname = "+".join(aname.split("|"))
    newline = "'%s', '%s', '%s'" % (laccid, acode, aname)
    sql = 'insert into wpp_cellarea values (%s)'%newline
    print sql
    cur_new.execute(sql)
    db_new.commit()
    #break
