#!/usr/bin/env python
# Verify the location quality of vance algo.
from __future__ import division
import sys
import csv
import pprint as pp
import numpy as np
sys.path.append('/home/alexy/dev/src/wlan-pos/')
import geo
import online as pos
import config as cfg


fpath = 'dat/fpp_rawdata/cmri'

# reqfile format: 14 or 16 cols.
reqfile = '%s/req.csv' % fpath
# retfile format: macs,rsss,lat,lon,err, lat/lon idx:
retfile = '%s/ret.csv' % fpath
ilat_cpp = 2; ilon_cpp = 3; ierr_cpp = 4
# outfile format: 
# macs               0,
# rsss               1, 
# ref(lat,lon)       2,3, 
# cpp(lat,lon,err)   4,5,6, 
# ecpp               7,
# py(lat,lon,err)    8,9,10,
# epy                11,
# e_cpp_py           12,
# ee                 13
outfile = '%s/reqreterr.csv' % fpath

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
    # addcols format: err_cpp, ee_cpp, py(lat,lon,err,ep,ee), ep_cpp_py, ee_cpp_py
    addcols = []
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
        mr = np.vstack((macs,rsss))
        mr = mr[:,idxs_max]
        pyloc = pos.fixPos(num_visAPs, mr, verb=False)
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
        print '%d: %s' % (i+1, addcol)
        addcols.append(addcol)
else:
    sys.exit('\nERROR: Not matched req/ret files: %s/%s!\n' % (reqfile, retfile))
print 'Done'

addcols = np.array(addcols)

means = np.mean(addcols[:,[0,1,5,6,7,8]], axis=0)
stds  =  np.std(addcols[:,[0,1,5,6,7,8]], axis=0)
maxs  =  np.max(addcols[:,[0,1,5,6,7,8]], axis=0)
print means
print stds
print maxs

reqreterr = np.append(reqret, addcols, axis=1)

sys.exit(0)
num_test = len(reqreterr)

idx_sort = np.argsort(ecpp)
errs_sort = ecpp[idx_sort]

err_67 = errs_sort[int(num_test*.67)]
err_95 = errs_sort[int(num_test*.95)]
perc_errless50  = (np.searchsorted(errs_sort,  50, side='right')+1)*100 / num_test 
perc_errless100 = (np.searchsorted(errs_sort, 100, side='right')+1)*100 / num_test 

print """
\nTotal: %d
%s
Mean: %.2f(m), Max: %.2f(m), Std: %.2f(m)
%s
67%%/95%%: %.2f(m)/%.2f(m), <50(m)/100(m): %.2f%%/%.2f%%""" %\
(num_test, '-'*45, mean, max, std, '-'*55, err_67, err_95, perc_errless50, perc_errless100)

np.savetxt(outfile, reqreterr, fmt='%s',delimiter=',')
print '\nDumping req/ret/err to: %s ... Done' % outfile

errs_sort = [ [x] for x in errs_sort ]
np.savetxt('errsort.dat', errs_sort, fmt='%s',delimiter=',')
