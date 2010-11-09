#-*- encoding=utf8 -*-
DATPATH = 'dat/'
LOCPATH = DATPATH+ 'loc/'
RAWSUFFIX = '.raw'
RMPSUFFIX = '.rmp'
LOCSUFFIX = '.loc'
#INTERSIZE = 10
CLUSTERKEYSIZE = 4
KNN = 4
KWIN = 1.25
RADIUS = 6372797 #meter

# DB related configuration.
dsn_local_ora = "yxt/yxt@localhost:1521/XE"
dsn_vance_ora = "mwlan/mwlan_pw@192.168.35.202/wlandb"
dsn_local_pg  = "host=localhost dbname=wppdb user=yxt password=yxt port=5433"
dbtype_ora = 'oracle' 
dbtype_pg  = 'postgresql'
dbtype_my  = 'mysql'
db_config_my = {
            'hostname' : 'localhost',
            'username' : 'pos',
            'password' : 'pos',
              'dbname' : 'wlanpos' }
# SQL table related data structs.
tbl_names_my = { 'cidaps':'cidaps', 
                   'cfps':'cfps' }
tbl_field_my = { 'cidaps':'(cid, keyaps)',
                   'cfps':'(cid, spid, lat, lon, rsss)' }
tbl_forms_my = {'cidaps':""" (
                     cid SMALLINT NOT NULL, 
                  keyaps VARCHAR(1024),
                   INDEX icid (cid)
                )""", 
                'wpp_cfps':""" (
                     cid SMALLINT NOT NULL,
                    spid SMALLINT NOT NULL,
                     lat DOUBLE(9,6),
                     lon DOUBLE(9,6),
                    rsss VARCHAR(255),
                   INDEX icid (cid)
                )""" }
tbl_names = ( 'wpp_clusteridaps','wpp_cfps' )
tbl_field = { 'wpp_clusteridaps':'(clusterid, keyaps, seq)',
                      'wpp_cfps':'(clusterid, lat, lon, height, rsss, cfps_time)',
                'wpp_uprecsinfo':'(spid,servid,time,imsi,imei,useragent,mcc,mnc,lac,cellid,cellrss,\
                                    lat,lon,height,wlanidentifier,wlanmatcher)',
                        'tsttbl':'(clusterid, keyaps, seq)' }
tbl_idx =   { 'wpp_clusteridaps':['clusterid','keyaps'], #{table_name:{'field_name'}}
                      'wpp_cfps':['clusterid'],
                        'tsttbl':['clusterid']}
tbl_files = { 'wpp_clusteridaps':'tbl/cidaps.tbl', 
                        'cidaps':'tbl/cidaps.tbl',
                      'wpp_cfps':'tbl/cfprints.tbl',
                        'tsttbl':'tbl/tsttbl.tbl' }
tbl_forms = { 'oracle':{
                'wpp_clusteridaps':""" (  
                     clusterid INT NOT NULL, 
                        keyaps VARCHAR2(71) NOT NULL,
                           seq INT NOT NULL)""", 
                'wpp_cfps':""" (  
                     clusterid INT NOT NULL,
                           lat NUMBER(9,6) NOT NULL,
                           lon NUMBER(9,6) NOT NULL,
                        height NUMBER(5,1) DEFAULT 0,
                          rsss VARCHAR2(100) NOT NULL,
                     cfps_time VARCHAR2(20))""",
                'wpp_uprecsinfo':""" (  
                            id INT PRIMARY KEY,	
                          spid INT,
                        servid INT,
                          time VARCHAR(20),
                          imsi VARCHAR(20),
                          imei VARCHAR(20),
                     useragent VARCHAR(300),
                           mcc INT,
                           mnc INT,
                           lac INT,
                        cellid INT,
                       cellrss VARCHAR(5),
                           lat NUMERIC(9,6),
                           lon NUMERIC(9,6),
                        height NUMERIC(5,1),
                wlanidentifier VARCHAR(1024),
                   wlanmatcher VARCHAR(255))""",
                'tsttbl':"""(
                     clusterid INT, 
                        keyaps VARCHAR2(71) NOT NULL,
                           seq INT NOT NULL)""" },
              'postgresql':{
                'wpp_clusteridaps':"""(
                     clusterid INT NOT NULL, 
                        keyaps VARCHAR(360) NOT NULL,
                           seq INT NOT NULL)""", 
                'wpp_cfps':""" (  
                     clusterid INT NOT NULL,
                           lat NUMERIC(9,6) NOT NULL,
                           lon NUMERIC(9,6) NOT NULL,
                        height NUMERIC(5,1) DEFAULT 0,
                          rsss VARCHAR(100) NOT NULL,
                     cfps_time VARCHAR(20))""",
                'wpp_uprecsinfo':""" (  
                            id INT PRIMARY KEY,	
                          spid INT,
                        servid INT,
                          time VARCHAR(20),
                          imsi VARCHAR(20),
                          imei VARCHAR(20),
                     useragent VARCHAR(300),
                           mcc INT,
                           mnc INT,
                           lac INT,
                        cellid INT,
                       cellrss VARCHAR(5),
                           lat NUMERIC(9,6),
                           lon NUMERIC(9,6),
                        height NUMERIC(5,1),
                wlanidentifier VARCHAR(1024),
                   wlanmatcher VARCHAR(255))""",
                'tsttbl':"""(
                     clusterid INT, 
                        keyaps VARCHAR2(71) NOT NULL,
                           seq INT NOT NULL)""" }}
# SQL statements.
sqls = { 'SQL_SELECT' : "SELECT %s FROM %s",
         'SQL_DROPTB' : "DROP TABLE %s PURGE",
         'SQL_INSERT' : "INSERT INTO %s %s VALUES %s",
        'SQL_TRUNCTB' : "TRUNCATE TABLE %s",
        'SQL_DROP_MY' : "DROP TABLE IF EXISTS %s",
       'SQL_CREATETB' : "CREATE TABLE %s %s",
      'SQL_CREATEIDX' : "CREATE INDEX %s ON %s(%s)",
     'SQL_CREATEUIDX' : "CREATE UNIQUE INDEX %s ON %s(%s)",
    'SQL_CREATETB_MY' : "CREATE TABLE IF NOT EXISTS %s %s",
       'SQL_CSVIN_MY' : """
                        LOAD DATA LOCAL INFILE "%s" INTO TABLE %s 
                        FIELDS TERMINATED BY ',' 
                        LINES TERMINATED BY '\\n' 
                        %s""" }

# String length of 179 and 149 chars are used for each intersection set to have 
# at most INTERSET APs, which should be enough for classification, very ugly though.
#dt_rmp_nocluster = {'names':('spid','lat','lon','macs','rsss'), 
#                  'formats':('i4','f4','f4','S179','S149')}
WLAN_FAKE = {
        1: #home
            [ ['00:25:86:23:A4:48', '-86'], ['00:24:01:FE:0F:20', '-90'], 
              ['00:0B:6B:3C:75:34', '-89'] ],
        2: #home-only 1 visible
            [ ['00:0B:6B:3C:75:34', '-89'] ],
        3: #cmri-only 1 visible
            [ ['00:15:70:9E:91:60', '-53'] ],
        4: #cmri-fail
            [ ['00:15:70:9F:7D:88', '-82'], ['00:15:70:9F:7D:89', '-77'],
              ['00:15:70:9F:7D:8A', '-77'], ['00:23:89:3C:BD:F2', '-81'],
              ['00:11:B5:FD:8B:6D', '-81'], ['00:23:89:3C:BE:10', '-70'],
              ['00:23:89:3C:BE:11', '-70'], ['00:23:89:3C:BE:13', '-71'],
              ['00:15:70:9E:91:62', '-72'], ['00:15:70:9E:91:60', '-49'],
              ['00:23:89:3C:BD:32', '-75'], ['00:15:70:9E:91:61', '-50'],
              ['00:23:89:3C:BE:12', '-75'], ['00:23:89:3C:BD:33', '-76'],
              ['00:14:BF:1B:A5:48', '-79'], ['00:15:70:9E:6C:6D', '-68'],
              ['00:15:70:9E:6C:6C', '-68'], ['00:15:70:9E:6C:6E', '-68'],
              ['00:23:89:3C:BD:30', '-75'], ['00:23:89:3C:BD:31', '-75'],
              ['00:23:89:3C:BC:90', '-79'], ['00:23:89:3C:BC:93', '-75'],
              ['00:11:B5:FE:8B:6D', '-88'], ['00:23:89:3C:BC:91', '-80'],
              ['00:23:89:3C:BC:92', '-81'], ['00:23:89:3C:BD:F1', '-80']],
        5: #cmri-ok-part
            [ ['00:15:70:9F:7D:8A', '-76'], ['00:15:70:9F:7D:88', '-77'],
              ['00:15:70:9F:7D:89', '-80'], ['00:11:B5:FD:8B:6D', '-79'],
              ['00:23:89:3C:BC:90', '-75'], ['00:23:89:3C:BC:91', '-76'],
              ['00:23:89:3C:BC:92', '-76'], ['00:23:89:3C:BC:93', '-75'],
              ['00:23:89:3C:BE:12', '-73'], ['00:23:89:3C:BE:10', '-75'],
              ['00:23:89:3C:BE:11', '-69'], ['00:15:70:9E:91:61', '-63'],
              ['00:23:89:3C:BE:13', '-71'], ['00:15:70:9E:91:62', '-61'],
              ['00:15:70:9E:91:60', '-62'], ['00:14:BF:1B:A5:48', '-81'],
              ['00:23:89:3C:BD:33', '-73'], ['00:15:70:9E:6C:6C', '-67'],
              ['00:15:70:9E:6C:6D', '-68'], ['00:15:70:9E:6C:6E', '-67']],
        6: #cmri-ok-full
            [ ['00:11:B5:FD:8B:6D', '-69'], ['00:15:70:9E:91:60', '-52'], 
              ['00:15:70:9E:91:61', '-53'], ['00:15:70:9F:73:64', '-78'], 
              ['00:15:70:9F:73:66', '-75'], ['00:15:70:9E:91:62', '-55'],
              ['00:23:89:3C:BE:10', '-74'], ['00:23:89:3C:BE:11', '-78'], 
              ['00:23:89:3C:BE:12', '-78'], ['00:11:B5:FE:8B:6D', '-80'], 
              ['00:15:70:9E:6C:6C', '-65'], ['00:15:70:9E:6C:6D', '-60'],
              ['00:15:70:9E:6C:6E', '-70'], ['00:15:70:9F:76:E0', '-81'], 
              ['00:15:70:9F:7D:88', '-76'], ['00:15:70:9F:73:65', '-76'], 
              ['00:23:89:3C:BD:32', '-75'], ['00:23:89:3C:BD:30', '-78'],
              ['02:1F:3B:00:01:52', '-76'] ],
        7: #cmri-square-fail
            [ ['00:16:16:1F:14:E0', '-49'], ['00:16:16:1E:EB:60', '-78'] ],
        8: #hq-fail
            [ ['00:60:B3:C9:61:27', '-63'], ['00:16:16:1E:B9:80', '-64'],
              ['00:1A:70:FB:B8:7F', '-65'], ['00:17:7B:0F:16:D9', '-66'] ],
        9: #hq-fail
            [ ['00:60:B3:C9:61:27', '-61'], ['00:1B:54:25:86:40', '-64'],
              ['00:17:7B:0F:16:D8', '-66'], ['00:17:7B:0F:16:D9', '-65'] ],
        10:#hq-ok
            [ ['00:60:B3:C9:61:27', '-64'], ['00:1E:E3:E0:69:40', '-64'],
              ['00:17:7B:0F:16:D8', '-66'], ['00:16:16:1E:B9:80', '-65'] ],
        11:#hq-fail
            [ ['00:60:B3:C9:61:27', '-66'], ['00:16:16:1E:82:20', '-67'],
              ['00:17:7B:0F:16:D8', '-67'], ['00:16:16:1F:24:A0', '-67'] ],
        12:#hq-fail
            [ ['00:60:B3:C9:61:27', '-63'], ['00:16:16:1E:B9:80', '-66'],
              ['00:17:7B:0F:16:D8', '-66'], ['00:16:16:1E:78:C0', '-69'] ],
        13:#hq-fail
            [ ['00:60:B3:C9:61:27', '-65'], ['00:17:7B:0F:16:D9', '-67'],
              ['00:17:7B:0F:16:DA', '-67'], ['00:1B:53:6C:E7:B0', '-67'] ],
        14:#hq-fail
            [ ['00:60:B3:C9:61:27', '-64'], ['00:17:7B:0F:16:D9', '-69'],
              ['00:16:16:1E:B9:80', '-65'], ['00:16:16:1F:30:60', '-68'] ],
        15:#hq-fail
            [ ['00:60:B3:C9:61:27', '-65'], ['00:17:7B:0F:16:D9', '-67'],
              ['00:1B:54:25:86:40', '-64'], ['00:16:16:1F:30:60', '-66'] ],
        16:#hq-fail
            [ ['00:60:B3:C9:61:27', '-65'], ['00:17:7B:0F:16:D9', '-66'],
              ['00:1B:54:25:86:40', '-66'], ['00:17:7B:0F:16:D8', '-66'] ],
        17:#hq-fail-dknn_0_and_1
            [ ['00:1E:E3:E0:69:40', '-66'], ['00:1D:7E:51:E0:8D', '-69'],
              ['00:16:16:1E:82:20', '-69'], ['00:17:7B:0F:16:D8', '-69'] ],
        18:#hq-square-interpolated-between-1313-and-902
            [ ['00:23:89:5F:D8:A1', '-71'], ['00:15:70:D0:52:60', '-71'],
              ['00:15:70:D0:52:61', '-73'], ['00:23:89:5C:9E:D0', '-73'] ],
        19:#hq-square
            [ ['00:17:7B:FC:34:70', '-60'], ['00:15:70:D0:52:62', '-65'],
              ['00:23:89:3C:BD:12', '-67'], ['00:15:70:D0:52:60', '-67'] ],
        20:#hq-square
            [ ['00:17:7B:FC:34:70', '-61'], ['00:15:70:D0:52:62', '-68'],
              ['00:15:70:D0:52:61', '-68'], ['00:23:89:3C:BD:13', '-69'] ],
}
icon_types = { 'on': [ '"encrypton"',  '/kml/icons/encrypton.png'],
              'off': [ '"encryptoff"', '/kml/icons/encryptoff.png'],
           'reddot': [ '"reddot"',     '/kml/icons/reddot.png'],
          'bluedot': [ '"bluedot"',    '/kml/icons/bluedot.png'],
        'yellowdot': [ '"yellowdot"',  '/kml/icons/yellowdot.png'],
             'wifi': [ '"wifi"',       '/kml/icons/wifi.png'],
        'dotshadow': [ '"dotshadow"',  '/kml/icons/dotshadow.png'],
}

props_jpg = {'term':'jpeg', # MUST be recognized by Gnuplot.
         'outfname':'cdf.jpg',
             'font':'"/usr/share/fonts/truetype/arphic/gbsn00lp.ttf, 14"',
             'size':'', # default: 1,1
            'title':'误差累积函数',
           'xlabel':'误差/米',
           'ylabel':'概率',
           'legend':'',
              'key':'right bottom',
           'xrange':[0,100],
           'yrange':[0,1],
            'xtics':'nomirror 10',
            'ytics':'nomirror .05',
             'grid':'x y', # default: off
           'border':3,
             'with':'lp pt 3 lc 1'}
props_mp = { 'term':'mp latex', # MUST be recognized by Gnuplot.
         'outfname':'cdf.mp',
             'font':'"Romans" 7',
             'size':'.8, .8', # default: 1,1
            'title':'CDF',
           'xlabel':'error/m',
           'ylabel':'probability',
           'legend':'',
              'key':'right bottom',
           'xrange':[0,100],
           'yrange':[0,1],
            'xtics':'nomirror 10',
            'ytics':'nomirror .05',
             'grid':'x y', # default: off
           'border':3,
             'with':'lp pt 4'}
