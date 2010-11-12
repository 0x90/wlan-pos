#!/usr/bin/env python
# collect test results and analyze the statistics of the data.
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
from config import TXTCOLORS as colors
sys.path.append('/home/alexy/dev/src/wlan-pos/tool/')
import geolocation_api as gl
import dataviz as viz


fpath = 'dat/fpp_rawdata/cmri'

boundry = 200

# reqfile format: 14 or 16 cols.
reqfile = '%s/req.csv' % fpath
# retfile format: macs,rsss,lat,lon,err, lat/lon idx:
retfile = '%s/ret.csv' % fpath
ilat_cpp = 2; ilon_cpp = 3; ierr_cpp = 4
# datafile format:    whole             in addcols
# macs                  0,                    
# rsss                  1,      
# ref(lat,lon)          2,3,    
# cpp(lat,lon,err)      4,5,6,          
# ecpp                  7,              0,      
# ee_cpp                8,              1,      
# py(lat,lon,err)       9,10,11,        2,3,4,    
# epy                   12,             5,
# ee_py                 13,             6,
# e_cpp_py              14,             7,
# ee_cpp_py             15,             8,
# google(lat,lon,err)   16,17,18,       9,10,11
# err_google            19,             12,
# ee_google             20,             13,
                                       
algos = ('cpp','py','google')
# addcols format: err_cpp, ee_cpp, py(lat,lon,err,ep,ee), ep_cpp_py, ee_cpp_py
idxs_addcols = { # idxs of all evaluated cols in addcols.
         'err_cpp':0,     'ee_cpp':1,
          'lat_py':2,     'lon_py':3,      'pyerr':4,      'err_py':5,      'ee_py':6, 
      'err_cpp_py':7,  'ee_cpp_py':8,
      'lat_google':9, 'lon_google':10, 'googleerr':11, 'err_google':12, 'ee_google':13
}
istats = [ # indexs of cols which are to be analyzed.
      idxs_addcols['err_cpp'], idxs_addcols['ee_cpp'], 
      idxs_addcols['err_py'],  idxs_addcols['ee_py'], 
      idxs_addcols['err_cpp_py'], idxs_addcols['ee_cpp_py'],
      idxs_addcols['err_google'], idxs_addcols['ee_google']
]
ierr_in_istats = {'cpp':[0,1], 'py':[2,3], 'google':[6,7]}


def collectData(reqret=None):
    # addcols format: err_cpp, ee_cpp, py(lat,lon,err,ep,ee), ep_cpp_py, ee_cpp_py, google(lat,lon,err,ep,ee)
    addcols = []; idiffs = []; atoken = None
    isErrinRange={'cpp':0, 'py':0, 'google':0}
    for i in xrange(len(reqret)):
        macs = np.array(macrss[i,0]); rsss = np.array(macrss[i,1])
        latref = reqret[i,0]; lonref = reqret[i,1]; latcpp = reqret[i,2]; loncpp = reqret[i,3] 
        cpperr = reqret[i,4]; addcol = []

        # cpploc error to refloc.
        err_cpp = geo.dist_km(loncpp, latcpp, lonref, latref)*1000
        addcol.append(err_cpp)
        # cpp error estimation error.
        ee = cpperr - err_cpp 
        if ee >= 0: isErrinRange['cpp'] += 1
        ee_cpp = abs(ee)/cpperr
        addcol.append(ee_cpp)

        # pyloc result.
        num_visAPs = len(macs)
        INTERSET = min(cfg.CLUSTERKEYSIZE, num_visAPs)
        idxs_max = np.argsort(rsss)[:INTERSET]
        mr = np.vstack((macs, rsss))[:,idxs_max]
        pyloc = wlanpos.fixPos(num_visAPs, mr, verb=False)
        addcol.extend(pyloc)
        # pyloc error to refloc.
        err_py = geo.dist_km(pyloc[1], pyloc[0], lonref, latref)*1000
        addcol.append(err_py)
        # py error estimation error.
        ee = pyloc[2] - err_py 
        if ee >= 0: isErrinRange['py'] += 1
        ee_py = abs(ee)/pyloc[2]
        addcol.append(ee_py)

        # pyloc error to cpploc.
        err_cpp_py = geo.dist_km(pyloc[1], pyloc[0], loncpp, latcpp)*1000
        addcol.append(err_cpp_py)
        # error between cpploc error & pyloc error.
        ee_cpp_py = abs(err_cpp - err_py)
        addcol.append(ee_cpp_py)
        if err_cpp_py or ee_cpp_py: idiffs.append(i)

        # google location api results.
        mr = mr.tolist()
        # Old interface of makeReq.
        #gloc_req = gl.makeReq(wlans=mr, atoken=atoken)
        wlans = []
        for i,mac in enumerate(mr[0]):
            wlan = {}
            wlan['mac_address'] = mac
            wlan['signal_strength'] = mr[1][i]
            wlans.append(wlan)
        gloc_req = gl.makeReq(wlans=wlans, atoken=atoken)
        gloc_ret = gl.getGL(gloc_req)
        gloc_pos = gloc_ret['location']
        if (not atoken) and ('access_token' in gloc_ret):
            atoken = gloc_ret['access_token']
        addcol.extend( gloc_pos.values() )
        # google loc error to refloc.
        err_google = geo.dist_km(gloc_pos['longitude'], gloc_pos['latitude'], lonref, latref)*1000
        addcol.append(err_google)
        # google loc error estimation error.
        ee = gloc_pos['accuracy'] - err_google 
        if ee >= 0: isErrinRange['google'] += 1
        ee_google = abs(ee)/gloc_pos['accuracy']
        addcol.append(ee_google)

        print '%d: %s' % (i+1, addcol)
        addcols.append(addcol)
        print 

    return (addcols, isErrinRange)


if __name__ == '__main__':
    arglen = len(sys.argv)
    if (not arglen==1) and (not arglen==2):
        sys.exit('\nPlease type: %s [label]\n' % (sys.argv[0]))
    else:
        if arglen == 2:
            label = sys.argv[1]
        else:
            label = 'urban'

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
    else:
        sys.exit('\nERROR: Not matched req/ret files: \n%s\n%s!\n' % (reqfile, retfile))
    print 'Done'

    sys.stdout.write('Slicing & Merging test data ... ')
    macrss = np.char.array(req[ :, [idx_macs,idx_rsss] ]).split('|')
    reqcols = [ idx_lat, idx_lon ]
    retcols = [ ilat_cpp, ilon_cpp, ierr_cpp ]
    # reqret format: ref(lat,lon), cpp(lat,lon,err)
    reqret = np.append(req[:,reqcols], ret[:,retcols], axis=1).astype(float)
    print 'Done'

    #gl.setConn()

    #print 'Reconstructing data matrix: Add python/google test results ... '
    # build data matrix with online google geolocation api request.
    #addcols, isErrinRange = collectData(reqret)
    #addcols = np.array( addcols )

    # build data matrix with offline csv data file.
    print 'Loading data matrix...'
    reqreterr_csv = csv.reader( open('test.csv','r') )
    # 7: start idx of addcols in reqreterr.
    addcols = np.array([ line for line in reqreterr_csv ])[:,7:].astype(float) 


    num_test = len(addcols)
    print 'Test count: %d' % num_test

    means = np.mean(addcols[:,istats], axis=0).round(2)
    stds  =  np.std(addcols[:,istats], axis=0).round(2)
    maxs  =  np.max(addcols[:,istats], axis=0).round(2)
    print 'means:'; pp.pprint(means)
    print 'stds:'; pp.pprint(stds)
    print 'maxs:'; pp.pprint(maxs)

    stats = {}
    for algo in algos:
        stats[algo] = {}
        idx_ep = ierr_in_istats[algo][0]; idx_ee = ierr_in_istats[algo][1]

        stats[algo]['errinrange'] = '%.2f%%'%(isErrinRange[algo]*100/num_test)

        stats[algo]['ep_mean'] = '%.2f'%means[idx_ep]
        stats[algo]['ep_std']  = '%.2f'%stds[idx_ep]
        stats[algo]['ep_max']  = '%.2f'%maxs[idx_ep]
        stats[algo]['ee_mean'] = '%.2f'%means[idx_ee]
        stats[algo]['ee_std']  = '%.2f'%stds[idx_ee]
        stats[algo]['ee_max']  = '%.2f'%maxs[idx_ee]

    for item in ('err_cpp','err_py','err_google'):
        name = item.split('_')[1]
        data = addcols[:,idxs_addcols[item]]
        idx_sort = np.argsort(data)
        data_sort = data[idx_sort]

        stats[name]['ep_67perc'] = '%.2f'%(data_sort[int(num_test*.67)])
        stats[name]['ep_95perc'] = '%.2f'%(data_sort[int(num_test*.95)])
        stats[name]['perc_epless50']  = '%.2f%%'%((np.searchsorted(data_sort,  50, side='right'))*100 / num_test)
        stats[name]['perc_epless100'] = '%.2f%%'%((np.searchsorted(data_sort, 100, side='right'))*100 / num_test)

    # idxs of position err col in addcols.
    idxs_eps_in_addcols = [idxs_addcols['err_cpp'], idxs_addcols['err_py'], idxs_addcols['err_google']] 
    idxs_sort = np.argsort(addcols[:,idxs_eps_in_addcols], axis=0).T
    idxs_sort200 = []
    # stats for tests that have location err less than 200.
    for idx,algo in enumerate(algos): # FIXME: algos name mapping to idx.
        idx_errless200 = np.searchsorted(addcols[idxs_sort[idx],idxs_eps_in_addcols[idx]], boundry)
        idx_sort200 = idxs_sort[idx][:idx_errless200]
        addcols_200 = addcols[idx_sort200,idxs_eps_in_addcols[idx]]
        num_test = len(addcols_200)
        stats[algo]['ep_mean_200'] = '%.2f'%(np.mean(addcols_200))
        stats[algo]['ep_std_200'] = '%.2f'%(np.std(addcols_200))
        stats[algo]['ep_max_200'] = '%.2f'%(np.max(addcols_200))
        stats[algo]['ep_67perc_200'] = '%.2f'%(addcols_200[int(num_test*.67)])
        stats[algo]['ep_95perc_200'] = '%.2f'%(addcols_200[int(num_test*.95)])
        stats[algo]['perc_epless50_200']  = '%.2f%%'%((np.searchsorted(addcols_200,  50, side='right'))*100 / num_test)
        stats[algo]['perc_epless100_200'] = '%.2f%%'%((np.searchsorted(addcols_200, 100, side='right'))*100 / num_test)

        viz.pyplotCDF(addcols_200, '%s_%s%s'%(algo,label,'200'))
        viz.pyplotCDF(addcols[:,idxs_eps_in_addcols[idx]], '%s_%s'%(algo,label))

    #pp.pprint(stats)
    sys.exit(0)

    # data/log file config.
    timestamp = time.strftime('%Y%m%d-%H%M%S')
    datafile = '%s/reqreterr_wpp_%s_%s.csv' % (fpath, label, timestamp)
    statsfile = '%s/stats_wpp_%s_%s.log' % (fpath, label, timestamp)
    diffile = '%s/diffs_wpp_%s_%s.csv' % (fpath, label, timestamp)

    # shelved data dumping.
    stats_dict = shlv.open(statsfile)
    for algo in algos:
        stats_dict[algo] = stats[algo]
    stats_dict.close()
    print 'stats results shelved into %s' % statsfile

    # shelved data reading.
    #stats_dict = dict(shlv.open(statsfile))
    #pp.pprint(stats_dict)

    reqreterr = np.append(reqret, addcols, axis=1)
    reqreterr = np.append(req[ :, [idx_macs,idx_rsss] ], reqreterr, axis=1)
    #diffs = reqreterr[idiffs,:]
    #print 'diff num: %d' % len(idiffs)

    np.savetxt(datafile, reqreterr, fmt='%s',delimiter=',')
    print '\nDumping all req/ret/err to: %s ... Done' % datafile

    #np.savetxt(diffile, diffs, fmt='%s',delimiter=',')
    #print '\nDumping diff req/ret/err to: %s ... Done' % diffile

    #errs_sort = [ [x] for x in errs_sort ]
    #np.savetxt('errsort.dat', errs_sort, fmt='%s',delimiter=',')
