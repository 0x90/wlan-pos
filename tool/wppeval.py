#!/usr/bin/env python
# Verify the location quality of vance algo.
from __future__ import division
import sys
import csv
import urllib2 as ul
import time
import shelve as shlv
import pprint as pp
import numpy as np

sys.path.append('/home/alexy/dev/src/wlan-pos/')
import geo
import online as wlanpos
import config as cfg
sys.path.append('/home/alexy/dev/src/wlan-pos/tool/')
import geolocation_api as gl


fpath = 'dat/fpp_rawdata/cmri'

# reqfile format: 14 or 16 cols.
reqfile = '%s/req.csv' % fpath
# retfile format: macs,rsss,lat,lon,err, lat/lon idx:
retfile = '%s/ret.csv' % fpath
ilat_cpp = 2; ilon_cpp = 3; ierr_cpp = 4
# outfile format: 
# macs                  0,
# rsss                  1, 
# ref(lat,lon)          2,3, 
# cpp(lat,lon,err)      4,5,6, 
# ecpp                  7,
# py(lat,lon,err)       8,9,10,
# epy                   11,
# e_cpp_py              12,
# ee                    13,
# google(lat,lon,err)   14,15,16,
# egoogle               17,
outfile = '%s/reqreterr.csv' % fpath
diffile = '%s/diffs.csv' % fpath

if __name__ == '__main__':
    gl.setConn()

    reqin = csv.reader( open(reqfile,'r') )
    retin = csv.reader( open(retfile,'r') )
    req = np.array([ line for line in reqin ])
    ret = np.array([ line for line in retin ])

    if len(req) == len(ret):
        num_cols = np.shape(req)[1]
        if num_cols == 14:
            idx_macs = 11; idx_rsss = 12
            idx_lat = 8; idx_lon = 9
        elif num_cols == 16:
            idx_macs = 14; idx_rsss = 15
            idx_lat = 11; idx_lon = 12
        else:
            sys.exit('\nERROR: Unsupported csv format!\n')
        print 'CSV format: %d fields\n' % num_cols

        print 'Slicing & Merging test data ... '
        macrss = np.char.array(req[ :, [idx_macs,idx_rsss] ]).split('|')
        reqcols = [ idx_lat, idx_lon ]
        retcols = [ ilat_cpp, ilon_cpp, ierr_cpp ]
        # reqret format: ref(lat, lon), cpp(lat,lon,err)
        reqret = np.append(req[:,reqcols], ret[:,retcols], axis=1).astype(float)
        # addcols format: err_cpp, ee_cpp, py(lat,lon,err,ep,ee), ep_cpp_py, ee_cpp_py, google(lat,lon,err,ep_google)
        addcols = []; idiffs = []
        atoken = None
        for i in xrange(len(reqret)):
            macs = np.array(macrss[i,0])
            rsss = np.array(macrss[i,1])
            latref = reqret[i,0]; lonref = reqret[i,1] 
            latcpp = reqret[i,2]; loncpp = reqret[i,3] 
            cpperr = reqret[i,4]
            addcol = []
            # cpploc error to refloc.
            err_cpp = geo.dist_km(loncpp, latcpp, lonref, latref)*1000
            addcol.append(err_cpp)
            # cpp error estimation error.
            ee_cpp = abs(err_cpp - cpperr)
            addcol.append(ee_cpp)
            # pyloc result.
            num_visAPs = len(macs)
            INTERSET = min(cfg.CLUSTERKEYSIZE, num_visAPs)
            idxs_max = np.argsort(rsss)[:INTERSET]
            mr = np.vstack((macs, rsss))
            mr = mr[:,idxs_max]
            pyloc = wlanpos.fixPos(num_visAPs, mr, verb=False)
            addcol.extend(pyloc)
            # pyloc error to refloc.
            err_py = geo.dist_km(pyloc[1], pyloc[0], lonref, latref)*1000
            addcol.append(err_py)
            # py error estimation error.
            ee_py = abs(err_py - pyloc[2])
            addcol.append(ee_py)
            # pyloc error to cpploc.
            err_cpp_py = geo.dist_km(pyloc[1], pyloc[0], loncpp, latcpp)*1000
            addcol.append(err_cpp_py)
            # error between cpploc error & pyloc error.
            ee = abs(err_cpp - err_py)
            addcol.append(ee)
            # google location api results.
            mr = mr.tolist()
            gloc_req = gl.makeReq(wlan=mr, atoken=atoken)
            gloc_ret = gl.getGL(gloc_req)
            gloc_pos = gloc_ret['location']
            if not atoken: 
                if 'access_token' in gloc_ret:
                    atoken = gloc_ret['access_token']
            addcol.extend( gloc_pos.values() )
            # google loc error to refloc.
            err_google = geo.dist_km(gloc_pos['longitude'], gloc_pos['latitude'], lonref, latref)*1000
            addcol.append(err_google)
            print '%d: %s' % (i+1, addcol)
            if err_cpp_py or ee: idiffs.append(i)
            addcols.append(addcol)
            print 
    else:
        sys.exit('\nERROR: Not matched req/ret files: %s/%s!\n' % (reqfile, retfile))
    print 'Done'

    addcols = np.array(addcols)

    # addcols format: err_cpp, ee_cpp, py(lat,lon,err,ep,ee), ep_cpp_py, ee_cpp_py
    idxs_addcols = { # idxs of all evaluated cols in addcols.
                 'err_cpp':0,
                  'ee_cpp':1,
                  'lat_py':2,
                  'lon_py':3,
                   'pyerr':4,
                  'err_py':5,
                   'ee_py':6,
              'err_cpp_py':7,
               'ee_cpp_py':8,
              'lat_google':9,
              'lon_google':10,
               'googleerr':11,
              'err_google':12
    }

    istats = [ # indexs of cols which are to be analyzed.
                idxs_addcols['err_cpp'], 
                idxs_addcols['ee_cpp'], 
                idxs_addcols['err_py'],
                idxs_addcols['ee_py'], 
                idxs_addcols['err_cpp_py'], 
                idxs_addcols['ee_cpp_py'],
                idxs_addcols['err_google'], 
    ]

    means = np.mean(addcols[:,istats], axis=0).round(2)
    stds  =  np.std(addcols[:,istats], axis=0).round(2)
    maxs  =  np.max(addcols[:,istats], axis=0).round(2)
    print 'means:'
    pp.pprint(means)
    print 'stds:'
    pp.pprint(stds)
    print 'maxs:'
    pp.pprint(maxs)

    reqreterr = np.append(reqret, addcols, axis=1)

    num_test = len(reqreterr)

    stats = {}
    stats['cpp'] = {}
    stats['cpp']['mean'] = '%.2f'%means[0]
    stats['cpp']['std']  = '%.2f'%stds[0]
    stats['cpp']['max']  = '%.2f'%maxs[0]
    stats['py'] = {}
    stats['py']['mean']  = '%.2f'%means[2]
    stats['py']['std']   = '%.2f'%stds[2]
    stats['py']['max']   = '%.2f'%maxs[2]
    stats['google'] = {}
    stats['google']['mean']  = '%.2f'%means[6]
    stats['google']['std']   = '%.2f'%stds[6]
    stats['google']['max']   = '%.2f'%maxs[6]

    for item in ('err_cpp','err_py','err_google'):
        name = item.split('_')[1]
        data = addcols[:,idxs_addcols[item]]
        idx_sort = np.argsort(data)
        data_sort = data[idx_sort]

        stats[name]['val_67perc'] = '%.2f'%(data_sort[int(num_test*.67)])
        stats[name]['val_95perc'] = '%.2f'%(data_sort[int(num_test*.95)])
        stats[name]['perc_errless50']  = '%.2f%%'%((np.searchsorted(data_sort,  50, side='right')+1)*100 / num_test)
        stats[name]['perc_errless100'] = '%.2f%%'%((np.searchsorted(data_sort, 100, side='right')+1)*100 / num_test)

    pp.pprint(stats)
    statsfile = 'stats.log'
    stats_dict = shlv.open(statsfile)
    stats_dict['cpp'] = stats['cpp']
    stats_dict['py'] = stats['py']
    stats_dict['google'] = stats['google']
    stats_dict.close()
    print 'stats results shelved into %s' % statsfile

    # shelve db reading for stats info.
    #stats_dict = dict(shlv.open(statsfile))
    #pp.pprint(stats_dict)

    #print """
    #\nTotal: %d
    #%s
    #Mean: %.2f(m), Max: %.2f(m), Std: %.2f(m)
    #%s
    #67%%/95%%: %.2f(m)/%.2f(m), <50(m)/100(m): %.2f%%/%.2f%%""" %\
    #(num_test, '-'*45, mean, max, std, '-'*55, err_67, err_95, perc_errless50, perc_errless100)

    reqreterr = np.append(req[ :, [idx_macs,idx_rsss] ], reqreterr, axis=1)
    diffs = reqreterr[idiffs,:]
    print 'diff num: %d' % len(idiffs)

    np.savetxt(outfile, reqreterr, fmt='%s',delimiter=',')
    print '\nDumping all req/ret/err to: %s ... Done' % outfile

    #np.savetxt(diffile, diffs, fmt='%s',delimiter=',')
    #print '\nDumping diff req/ret/err to: %s ... Done' % diffile

    #errs_sort = [ [x] for x in errs_sort ]
    #np.savetxt('errsort.dat', errs_sort, fmt='%s',delimiter=',')
