#!/usr/bin/env python
# Purpose: Road(name) matching using input point coord.
# Author: Sun Bing, Lu Huixin, Li Xiaoye, Yan Xiaotian.
# Lisence: GPL
# Date: 2008-12-02
# TODO: understand 'groub by' in sql.

from __future__ import division
import sys, os
from decimal import Decimal
sys.path.append(os.getcwd() + '/lib')
from MySQLdb import connect, cursors
from mapmatch import findBlks, vertPt, mapDist, isBetween

hostname = 'localhost' #!!!'59.64.183.198' if NOT on R60.
#hostname = '59.64.183.171' #!!!'59.64.183.198' if NOT on R60.
username = 'gps'
password = 'gps'
dbname   = 'road'

sqr_rad = 0.03 #Search area radius:30m.
#for road finding test.
#input = {'lon':116.355043,'lat':39.957536} #xingtan road.
#input = {'lon':116.367652,'lat':39.986047} #beisihuan road.
input = {'lon':116.3631791, 'lat':39.98625205} #north pt at zhixin-huayuan road
#input = {'lon':116.363205989,'lat':39.98568906} #south pt at zhixin-huayuan road

try:
	import psyco
	psyco.bind(findBlks)
	psyco.bind(vertPt)
	psyco.bind(mapDist)
	psyco.bind(isBetween)
	#psyco.profile()
	psyco.full(0.01)
except ImportError:
	pass

print "\nUser Position: (%f,%f)" % \
		(input['lon'], input['lat'])
blk_ids = findBlks(input, sqr_rad) #search range:100m.
print "Affiliated Blocks:(count:%d): %s" % \
		(blk_ids.__len__(),str(blk_ids))

try:
	cxn = connect(host=hostname, user=username, \
			passwd=password, db=dbname, compress=1)
			#cursorclass=cursors.DictCursor)
except MySQLdb.Error,e:
	print "Can NOT connect %s@server: %s!" % (username, hostname)
	print "Error(%d): %s" % (e.args[0], e.args[1])
	sys.exit(99)

#returned values indexed by field name(or field order if no arg).
cur = cxn.cursor(cursorclass=cursors.DictCursor)

#mdist: list of minimum distances of each blk(1:1w).
#mdist_blk: dictionary of mdist:blocks.
#blk_mpts: dictionary of block:min-distance-points(lon,lat).
mdist_blk={}; blk_mpts={}; mdist=[]

for blk in blk_ids:
	for mblk in blk_ids[blk]:
		print "-" * 60
		print "Searching Block: %s" % blk

		mysql = "select %s, count(%s) as npoints from %s where mblkid=%d group by %s"
		field = "id"
		cur.execute(mysql % (field,field,blk,mblk,field))
		plines= cur.fetchall() #every pline has the same roadid(like in MIF).

		mysql = 'select %s from %s where mblkid=%d'
		field = "lon, lat"
		cur.execute(mysql % (field,blk,mblk))
		points= cur.fetchall() 

		pline_base = 0; min_roadid = 0; min_dist = 1e5; min_point = {}

		for pline in plines:
			#input point M is start or end.
			if min_dist == 0 and min_point: break

			roadid  = pline['id']
			npoints = pline['npoints']

			if npoints == 1: #pline only has 1 point.
				only = points[pline_base]
				dist = mapDist(input, only)
				if dist < min_dist:
					min_roadid = roadid
					min_dist = dist 
					min_point= only
				pline_base += 1
				continue 

			#all segments in the same pline(roadid).
			for cnt in range( npoints - 1 ):
				if min_dist == 0 and min_point: break

				idx = pline_base + cnt
				start = points[idx]; end = points[idx+1]

				if start == end: #1 point.
					dist = mapDist(input, start)
					if dist < min_dist:
						min_roadid = roadid
						min_dist = dist 
						min_point= end
					continue 

				#input point M same as start or end.
				if (Decimal(str(input['lon'])) == start['lon'] and \
					Decimal(str(input['lat'])) == start['lat'] ) or \
				   (Decimal(str(input['lon'])) == end['lon'] and \
				    Decimal(str(input['lat'])) == end['lat'] ):
					min_dist = 0
					min_point = end
					min_roadid = roadid
					break

				vertpoint = vertPt(start, end, input)
				#discussion of point intersection P relative to input/start/end.
				if vertpoint == start:
					dist = mapDist(input, start)
				elif vertpoint == end:
					dist = mapDist(input, end)
				else:
					#point P between start and end or not.
					isbetween = isBetween(start, end, vertpoint)
					if isbetween == True:
						dist = mapDist(input, vertpoint) #spherical dist. 
					else:
						distA= mapDist(input, start)
						distB= mapDist(input, end)
						dist = min(distA, distB)

				if dist < min_dist: 
					min_dist = dist
					min_point= end
					min_roadid = roadid

			pline_base += npoints

		mdist_blk[min_dist]=blk
		blk_mpts[blk]=min_point
		mdist.append(min_dist)


mdist.sort()
min_blk=mdist_blk[mdist[0]]
mpts=blk_mpts[min_blk]

mysql = "select %s from %s where lon=%f and lat=%f"
field = "id,district,rname"
cur.execute(mysql % (field, min_blk, float(mpts['lon']), float(mpts['lat'])))
roads = cur.fetchall() 
cur.close(); cxn.close()

print "Result:\n\tBlock\t\tRoadID\tDistance(m)\tDistrict\tRoadName" 
print "\t" + "-"*80

if not roads:
	print "FAIL: Found NOTHING!"; sys.exit(99)
for road in roads:
	#if not road['rname'] and roads.__len__ != 1: continue
	print "\t%s\t%d\t%f\t%s\t%s" % \
		(min_blk, road['id'], mdist[0], road['district'], road['rname'])
print
