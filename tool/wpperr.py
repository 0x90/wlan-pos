#!/usr/bin/env python
# Verify the location quality of vance algo.
from __future__ import division
import sys
import csv
import pprint as pp
import numpy as np
sys.path.append('/home/alexy/dev/src/wlan-pos/')
import geo

#reqfile = 'req.csv'
#retfile = 'ret.csv'
fpath = 'dat/fpp_rawdata/cmri'
reqfile = '%s/req.csv' % fpath
retfile = '%s/ret.csv' % fpath
outfile = '%s/reqreterr.csv' % fpath
# retfile format: macs,rsss,lat,lon,err, lat/lon idx:
idx_lat_v = 2; idx_lon_v = 3

reqin = csv.reader( open(reqfile,'r') )
retin = csv.reader( open(retfile,'r') )
req = np.array([ line for line in reqin ])
ret = np.array([ line for line in retin ])

if len(req) == len(ret):
    num_cols = np.shape(req)[1]
    if num_cols == 14:
        idx_lat = 8; idx_lon = 9
    elif num_cols == 16:
        idx_lat = 11; idx_lon = 12
    else:
        sys.exit('\nERROR: Unsupported csv format!\n')
    print 'CSV format: %d fields\n' % num_cols

    sys.stdout.write('Slicing & Merging test data ... ')
    reqret = np.append(req[:,idx_lat:idx_lon+1], ret[:,idx_lat_v:idx_lon_v+1], axis=1).astype(float)
    errs = []
    for line in reqret:
        lat1 = line[0]; lon1 = line[1]; lat2 = line[2]; lon2 = line[3]
        err = geo.dist_km(lon1, lat1, lon2, lat2)*1000
        #print 'err: %f(m)' % err
        errs.append([err])
else:
    sys.exit('\nERROR: Not matched req/ret files: %s/%s!\n' % (reqfile, retfile))
print 'Done'

errs = np.array(errs)
reqreterr = np.append(reqret, errs, axis=1)

errs = np.ravel(errs)
num_test = len(errs)
mean = errs.mean()
std  = errs.std()

idx_sort = np.argsort(errs)
errs_sort = errs[idx_sort]
max  = errs_sort[-1]

err_65 = errs_sort[int(num_test*.65)]
err_97 = errs_sort[int(num_test*.97)]
perc_errless50  = (np.searchsorted(errs_sort,  50, side='right')+1)*100 / num_test 
perc_errless100 = (np.searchsorted(errs_sort, 100, side='right')+1)*100 / num_test 

print """
\nTotal: %d
%s
Mean: %.2f(m), Max: %.2f(m), Std: %.2f(m)
%s
65%%/97%%: %.2f(m)/%.2f(m), <50(m)/100(m): %.2f%%/%.2f%%""" %\
(num_test, '-'*45, mean, max, std, '-'*55, err_65, err_97, perc_errless50, perc_errless100)

np.savetxt(outfile, reqreterr, fmt='%s',delimiter=',')
print '\nDumping req/ret/err to: %s ... Done' % outfile

#errs_sort = [ [x] for x in errs_sort ]
#np.savetxt('errsort.dat', errs_sort, fmt='%s',delimiter=',')
