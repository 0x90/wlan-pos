import sys, time
from pprint import pprint
import shpUtils

filename = sys.argv[1]
print 'Loading shapefile %s...' % filename
t1 = time.time()
shps = shpUtils.loadShapefile( filename )
t2 = time.time()
print '[%0.3f] seconds load time' %( t2 - t1 )

for cnt in range(2):
    print '\n%d' % cnt
    pprint(shps[cnt])
