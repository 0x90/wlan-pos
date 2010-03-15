import sys, time
from struct import unpack
from pprint import pprint
import dbfUtils, math


shapeTypes = {0:'Null',    
              1:'Point',   3:'PolyLine',   5:'Polygon',   8:'MultiPoint',
             11:'PointZ', 13:'PolyLineZ', 15:'PolygonZ', 18:'MultiPointZ',
             21:'PointM', 23:'PolyLineM', 25:'PolygonM', 28:'MultiPointM',
             31:'MultiPatch' }

class Shapefile(object):
    #TODO: class method to handle file ptr

    def __init__(self, shpfile=None):
        self.shpfile = shpfile
        self.mainheader = {'fcode':None, 'version':0, 'flen':0, 'type':None, 
                            'bbox':{'Xmin':0, 'Xmax':0, 'Ymin':0, 'Ymax':0,
                                    'Zmin':0, 'Zmax':0, 'Mmin':0, 'Mmax':0  } }
        self.main_content = []
        self._parseHeader()
        if not self.mainheader['type'] == shapeTypes[0]:
            self._parseMainContent()


    def _parseHeader(self):
        """ Main file header """
        self.mainheader['fcode'] = self._unpackInt('>i')        
        self.shpfile.seek(24)
        self.mainheader['flen'] = self._unpackInt('>i')        
        self.mainheader['version'] = self._unpackInt('i')        

        self.shpfile.seek(32)
        self.mainheader['type'] = shapeTypes[ self._unpackInt('i') ]
        self.mainheader['bbox'] = self._parseBoundingbox()

    
    def _unpackInt(self, fmt):
        data = self.shpfile.read(4)
        if data == '': return data
        return unpack(fmt, data)[0]

    def _unpackDouble(self, fmt):
        data = self.shpfile.read(8)
        if data == '': return data
        return unpack(fmt, data)[0]

    def _unpack(self, fmt, data):
        if data == '': return data
        return unpack(fmt, data)[0]

    def _parseBoundingbox(self):
        bbox = {}
        bbox['Xmin'] = self._unpackDouble('d')
        bbox['Ymin'] = self._unpackDouble('d')
        bbox['Xmax'] = self._unpackDouble('d')
        bbox['Ymax'] = self._unpackDouble('d')
        return bbox

    def _parseMainContent(self):
        # Records contents
        self.shpfile.seek(100)
        while True:
            shp_record = self._parseRecord()
            if shp_record == None: break
            self.main_content.append(shp_record)

    def _parseRecord(self):
        # Record header
        record_number = self._unpackInt('>i')
        if record_number == '': return None
        content_length = self._unpackInt('>i')
        record_shape_type = self._unpackInt('i')

        # Read main contents
        shp_record = {}
        shp_record['type'] = shapeTypes[record_shape_type]
        if record_shape_type == 0: return shp_record # Null
        elif record_shape_type == 1:                 # Point
            shp_record = self._parseRecordPoint()
        elif record_shape_type == 3 or record_shape_type == 5: # PolyLine, Polygon
            shp_record = self._parseBoundingbox()
            shp_record['numparts']  = self._unpackInt('i')
            shp_record['numpoints'] = self._unpackInt('i')

            shp_record['parts'] = []
            for i in xrange(shp_record['numparts']):
                shp_record['parts'].append(self._unpackInt('i'))
            ptr_pts_start = self.shpfile.tell()

            pts_cnt = 0
            for idx_part in range(shp_record['numparts']):
                idx_1stpt = shp_record['parts'][idx_part] # Index of 1st part point in points array
                shp_record['parts'][idx_part] = {}
                shp_record['parts'][idx_part]['points'] = []
                
                prevPoint = []
                while (pts_cnt < shp_record['numpoints']):
                    currPoint = self._parseRecordPoint()
                    shp_record['parts'][idx_part]['points'].append(currPoint)
                    pts_cnt += 1
                    if not prevPoint or pts_cnt == 0: prevPoint = currPoint
                    elif currPoint == prevPoint: prevPoint = []; break
                    
            self.shpfile.seek(ptr_pts_start + (pts_cnt * 16)) # 16: point record storage cost
        elif record_shape_type == 8:                 # MultiPoint
            shp_record['bbox'] = self._parseBoundingbox()
            shp_record['numpoints'] = self._unpackInt('i')    
            shp_record['points'] = []
            for i in xrange(shp_record['numpoints']):
                shp_record['points'].append(self._parseRecordPoint())
        else: shp_record = None                      # Illigal shp type
        return shp_record

    def _parseRecordPoint(self):
        point = {}
        point['X'] = self._unpackDouble('d')
        point['Y'] = self._unpackDouble('d')
        return point


####
#### additional functions
####

def getCentroids(records, projected=False):
    # for each feature
    if projected:
        points = 'projectedPoints'
    else:
        points = 'points'
        
    for feature in records:
        numpoints = cx = cy = 0
        for part in feature['shp_data']['parts']:
            for point in part[points]:
                numpoints += 1
                cx += point['x']
                cy += point['y']
        cx /= numpoints
        cy /= numpoints
        feature['shp_data']['centroid'] = {'x':cx, 'y':cy}
                
        
def getBoundCenters(records):
    for feature in records:
        cx = .5 * (feature['shp_data']['xmax']-feature['shp_data']['xmin']) + feature['shp_data']['xmin']
        cy = .5 * (feature['shp_data']['ymax']-feature['shp_data']['ymin']) + feature['shp_data']['ymin']
        feature['shp_data']['boundCenter'] = {'x':cx, 'y':cy}
    
def getTrueCenters(records, projected=False):
    #gets the true polygonal centroid for each feature (uses largest ring)
    #should be spherical, but isn't

    if projected:
        points = 'projectedPoints'
    else:
        points = 'points'
        
    for feature in records:
        maxarea = 0
        for ring in feature['shp_data']['parts']:
            ringArea = getArea(ring, points)
            if ringArea > maxarea:
                maxarea = ringArea
                biggest = ring
        #now get the true centroid
        tempPoint = {'x':0, 'y':0}
        if biggest[points][0] != biggest[points][len(biggest[points])-1]:
            print "mug", biggest[points][0], biggest[points][len(biggest[points])-1]
        for i in range(0, len(biggest[points])-1):
            j = (i + 1) % (len(biggest[points])-1)
            tempPoint['x'] -= (biggest[points][i]['x'] + biggest[points][j]['x']) * ((biggest[points][i]['x'] * biggest[points][j]['y']) - (biggest[points][j]['x'] * biggest[points][i]['y']))
            tempPoint['y'] -= (biggest[points][i]['y'] + biggest[points][j]['y']) * ((biggest[points][i]['x'] * biggest[points][j]['y']) - (biggest[points][j]['x'] * biggest[points][i]['y']))
            
        tempPoint['x'] = tempPoint['x'] / ((6) * maxarea)
        tempPoint['y'] = tempPoint['y'] / ((6) * maxarea)
        feature['shp_data']['truecentroid'] = tempPoint
        

def getArea(ring, points):
    #returns the area of a polygon
    #needs to be spherical area, but isn't
    area = 0
    for i in range(0,len(ring[points])-1):
        j = (i + 1) % (len(ring[points])-1)
        area += ring[points][i]['x'] * ring[points][j]['y']
        area -= ring[points][i]['y'] * ring[points][j]['x']
            
    return math.fabs(area/2)
    

def getNeighbors(records):
    
    #for each feature
    for i in range(len(records)):
        #print i, records[i]['dbf_data']['ADMIN_NAME']
        if not 'neighbors' in records[i]['shp_data']:
            records[i]['shp_data']['neighbors'] = []
        
        #for each other feature
        for j in range(i+1, len(records)):
            numcommon = 0
            #first check to see if the bounding boxes overlap
            if overlap(records[i], records[j]):
                #if so, check every single point in this feature to see if it matches a point in the other feature
                
                #for each part:
                for part in records[i]['shp_data']['parts']:
                    
                    #for each point:
                    for point in part['points']:
                        
                        for otherPart in records[j]['shp_data']['parts']:
                            if point in otherPart['points']:
                                numcommon += 1
                                if numcommon == 2:
                                    if not 'neighbors' in records[j]['shp_data']:
                                        records[j]['shp_data']['neighbors'] = []
                                    records[i]['shp_data']['neighbors'].append(j)
                                    records[j]['shp_data']['neighbors'].append(i)
                                    #now break out to the next j
                                    break
                        if numcommon == 2:
                            break
                    if numcommon == 2:
                        break
                
                                    
                                
                                
def projectShapefile(records, whatProjection, lonCenter=0, latCenter=0):
    print 'projecting to ', whatProjection
    for feature in records:
        for part in feature['shp_data']['parts']:
            part['projectedPoints'] = []
            for point in part['points']:
                tempPoint = projectPoint(point, whatProjection, lonCenter, latCenter)
                part['projectedPoints'].append(tempPoint)

def projectPoint(fromPoint, whatProjection, lonCenter, latCenter):
    latRadians = fromPoint['y'] * math.pi/180
    if latRadians > 1.5: latRadians = 1.5
    if latRadians < -1.5: latRadians = -1.5
    lonRadians = fromPoint['x'] * math.pi/180
    lonCenter = lonCenter * math.pi/180
    latCenter = latCenter * math.pi/180
    newPoint = {}
    if whatProjection == "MERCATOR":
        newPoint['x'] = (180/math.pi) * (lonRadians - lonCenter)
        newPoint['y'] = (180/math.pi) * math.log(math.tan(latRadians) + (1/math.cos(latRadians)))
        if newPoint['y'] > 200:
            newPoint['y'] = 200
        if newPoint['y'] < -200:
            newPoint['y'] = 200
        return newPoint
    if whatProjection == "EQUALAREA":
        newPoint['x'] = 0
        newPoint['y'] = 0
        return newPoint
        

def overlap(feature1, feature2):
    if (feature1['shp_data']['xmax'] > feature2['shp_data']['xmin'] and feature1['shp_data']['ymax'] > feature2['shp_data']['ymin'] and feature1['shp_data']['xmin'] < feature2['shp_data']['xmax'] and feature1['shp_data']['ymin'] < feature2['shp_data']['ymax']):
        return True
    else:
        return False



if __name__ == '__main__':

    filename = sys.argv[1]
    print '\nLoading shapefile \'%s\'...' % filename
    t1 = time.time()
    shpfile = Shapefile(open(filename, 'rb'))
    t2 = time.time()
    print 'Elapsed time: %0.4f/sec' %( t2 - t1 )

    pprint(shpfile.mainheader)
    print 
    lenShps = len(shpfile.main_content)
    print 'Total valid shapes: %d' % lenShps
    pprint(shpfile.main_content[:2])
