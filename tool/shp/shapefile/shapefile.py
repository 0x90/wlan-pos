"""The shapefile class.

This class implements ESRI shapefiles as defined in the July 1998 whitepaper.

See http://www.esri.com/library/whitepapers/pdfs/shapefile.pdf
"""
__author__ = "Martin Lacayo-Emery <positrons@gmail.com>"
__date__ = "23 November 2006"

__credits__ = """Arzu \xc7\xf6ltekin, University of Z\xfcrich, project collaborator
Sara Fabrikant, University of Z\xfcrich, project collaborator
Andr\xe9 Skupin, San Diego State University, thesis advisor
University of Z\xfcrich, host institution
San Diego State University, home institution
Eidgen\xf6ssischen Stipendienkommission f\xfcr ausl\xe4ndische Studierende, host funding agency
Fulbright Program, host funding program
Department of Geography, San Diego State University, home funding
"""

import sys
import struct
import databasefile
import math

shapeTypes= {"Null Shape":0,"Point":1,"PolyLine":3,"Polygon":5,
             "MultiPoint":8,"PointZ":11,"PolyLineZ":13,
             "PolygonZ":15,"MultiPointZ":18,"PointM":21,
             "PolyLineM":23,"PolygonM":25,"MultiPointM":28,
             "MultiPatch":31}

class Shapefile:
    """
    Shapefile class supporting single point and single part polygon shapes.
    Shapes are passed in as a list of points.

    >>> s=Shapefile(1)
    >>> s.add([(0,0)])
    >>> s.add([(0,1)])
    >>> s.add([(1,1)])
    >>> s.add([(1,0)])
    >>> len(s)
    4
    >>> s[0]
    (0, 0)
    >>> import tempfile
    >>> shp=tempfile.TemporaryFile()
    >>> shx=tempfile.TemporaryFile()
    >>> s.write(shp,shx)
    >>> shp.seek(0,0)
    >>> shx.close()
    >>> t=Shapefile(1)
    >>> len(t)
    0
    >>> t.readShp(shp)
    >>> len(t)
    4
    >>> t[1]
    (0.0, 1.0)
    >>> shp.close()
    """
    #constructors
    def __init__(self,shapeType=1):
        """
        The constructor function creates an instance of the Shapefile class
        with an option shapeType parameter. The shapeTypes are coded using
        integers. Currently only point, polyline, and polygon are supported,
        which are coded as 1, 3, and 5 respectively. Further development may
        extend support the remaining shape types, which follow with their
        coding in paraenthesis: Null Shape (0), MultiPoint (8), PointZ (11),
        PolyLineZ (13), PolygonZ (15), MultiPointZ (18), PointM (21),
        PolyLineM (23), PolygonM (25), MultiPointM (28), and MultiPatch (31).
        """
        Xmin=0
        Ymin=0
        Xmax=0
        Ymax=0
        Zmin=0
        Zmax=0
        Mmin=0
        Mmax=0
        shapes=[]
        fieldnames=[]
        fieldspecs=[]
        records=[]

        self.fileCode=9994
        self.version=1000
        #number of 16-bit words
        self.size=50

        self.shapeType=shapeType
        self.Xmin=Xmin
        self.Ymin=Ymin
        self.Xmax=Xmax
        self.Ymax=Ymax
        self.Zmin=Zmin
        self.Zmax=Zmax
        self.Mmin=Mmin
        self.Mmax=Mmax

        if len(shapes)!=len(records):
            raise ValueError, "The number of shapes and table records must match."
        
        self.shapes=shapes
        self.table=databasefile.DatabaseFile(["ID"]+fieldnames,[('N', 6, 0)]+fieldspecs,records)

    #accessors
    def __len__(self):
        return len(self.shapes)

    def __getitem__(self,i):
        return self.shapes[i]

    def index(self,fieldname):
        return self.table.index(fieldname)
        
    #modifiers
    def add(self,shape,record=None):
        """
        Adds a shape object to the shapefile.
        Shape objects must a list of (x,y) tuples.
        Adding table records with shapes is not currently supported.
        """
        #adjust the bound box minmums and maximums
        for p in shape:
            if p[0]<self.Xmin:
                self.Xmin=p[0]
            elif p[0]>self.Xmax:
                self.Xmax=p[0]
            if p[1]<self.Ymin:
                self.Ymin=p[1]
            elif p[1]>self.Ymax:
                self.Ymax=p[1]

        #adjust the known file size accordingly
        if self.shapeType==1:
            self.size+=10
            self.shapes.append(shape.pop())
        elif self.shapeType==5 or self.shapeType==3:
            self.size+=28+(8*len(shape))
            self.shapes.append(shape)

        #assign the passed in record, or generate an id
        if record:
            raise ValueError, "Passing in table records is not currently supported"
        else:
            self.table.addRow([len(self.shapes)])

    #i/o
    def readFile(self,inName):
        if inName[inName.rfind("."):]==".shp":
            inName=inName[:inName.rfind(".")]
       
        inShp=open(inName+".shp",'rb')
        self.readShp(inShp)
        inShp.close()
        
        self.table=databasefile.DatabaseFile([],[],[],inName+".dbf")

    def readShp(self,inShp):
        #shp file header
        #byte 0, File Code
        self.fileCode,=struct.unpack('>i',inShp.read(4))
        print 'File Code: %d' % self.fileCode
        inShp.seek(24)   
        #byte 24, File Length, total length of file in 16-bit words
        size,=struct.unpack('>i',inShp.read(4))
        print 'File length: %d' % size
        #byte 28, Version, integer
        self.version,=struct.unpack('<i',inShp.read(4))
        print 'Version: %d' % self.version
        #byte 32, shape type
        self.shapeType,=struct.unpack('<i',inShp.read(4))
        if self.shapeType in shapeTypes.values():
            idx = shapeTypes.values().index(self.shapeType)
        print 'Shape type: %s' % shapeTypes.keys()[idx]
        #byte 36, Bounding Box Xmin
        self.Xmin,=struct.unpack('<d',inShp.read(8))
        #byte 44 Bounding Box Ymin
        self.Ymin,=struct.unpack('<d',inShp.read(8))
        #byte 52 Bounding Box Xmax
        self.Xmax,=struct.unpack('<d',inShp.read(8))
        #byte 60 Bounding Box Ymax
        self.Ymax,=struct.unpack('<d',inShp.read(8))
        #byte 68* Bounding Box Zmin
        self.Zmin,=struct.unpack('<d',inShp.read(8))
        #byte 76* Bounding Box Zmax
        self.Zmax,=struct.unpack('<d',inShp.read(8))
        #byte 84* Bounding Box Mmin
        self.Mmin,=struct.unpack('<d',inShp.read(8))
        #byte 92* Bounding Box Mmax
        self.Mmax,=struct.unpack('<d',inShp.read(8))
        print 'Boundaries:', \
                self.Xmin, self.Ymin, \
                self.Xmax, self.Ymax, \
                self.Zmin, self.Zmax, \
                self.Mmin, self.Mmax

        #read shapes
        if self.shapeType==1:
            for i in range((size-50)/10):
                id,=struct.unpack('>i',inShp.read(4))
                length,=struct.unpack('>i',inShp.read(4))
                shapeType,=struct.unpack('<i',inShp.read(4))
                x,=struct.unpack('<d',inShp.read(8))
                y,=struct.unpack('<d',inShp.read(8))
                self.add([(x,y)])
                               
        elif self.shapeType==5 or self.shapeType==3:
            #raise ValueError, "Sorry only poiny reading is currently supported."
            while inShp.tell()<(size*2):
                id,=struct.unpack('>i',inShp.read(4))
                length,=struct.unpack('>i',inShp.read(4))
                shapeType,=struct.unpack('<i',inShp.read(4))
                Xmin,=struct.unpack('<d',inShp.read(8))
                Ymin,=struct.unpack('<d',inShp.read(8))
                Xmax,=struct.unpack('<d',inShp.read(8))
                Ymax,=struct.unpack('<d',inShp.read(8))
                numParts,=struct.unpack('<i',inShp.read(4))
                numPoints,=struct.unpack('<i',inShp.read(4))
                print 'CurPtr: %d, id: %d, len: %d, shapeType: %d, X:(%d,%d), Y:(%d,%d), numParts: %d, numPoints: %d' % \
                        (inShp.tell(), id, length, shapeType, Xmin, Xmax, Ymin, Ymax, numParts, numPoints)

                if numParts!=1:
                    raise ValueError, "Sorry multipart shapes are not supported."

                parts=[]
                for i in range(numParts):
                    parts.append(struct.unpack('<i',inShp.read(4)))

                points=[]
                for i in range(numPoints):
                    x,=struct.unpack('<d',inShp.read(8))
                    y,=struct.unpack('<d',inShp.read(8))
                    points.append((x,y))
                self.add(points)
                    
        
    def writeFile(self,outName):
        if outName[outName.rfind("."):]==".shp":
            outName=outName[:outName.rfind(".")]
        outShp=open(outName+".shp",'wb')
        outShx=open(outName+".shx",'wb')
        outDbf=open(outName+".dbf",'wb')
        self.table.write(outDbf)
        outDbf.close()
        self.write(outShp,outShx)
        outShp.close()
        outShx.close()

    def write(self,shp,shx):
        """
        """
        #shp file header
        #byte 0, File Code
        shp.write(struct.pack('>i', self.fileCode))
        #byte 4, Unused
        shp.write(struct.pack('>i', 0))
        #byte 8, Unused
        shp.write(struct.pack('>i', 0))
        #byte 12, Unused
        shp.write(struct.pack('>i', 0))
        #byte 16, Unused
        shp.write(struct.pack('>i', 0))
        #byte 20, Unused
        shp.write(struct.pack('>i', 0))
        #byte 24, File Length, total length of file in 16-bit words
        #this must be determined after file creation.
        shp.write(struct.pack('>i', self.size))
        #byte 28, Version, integer
        shp.write(struct.pack('<i', self.version))
        #byte 32, shape type
        shp.write(struct.pack('<i',self.shapeType))
        #byte 36, Bounding Box Xmin
        shp.write(struct.pack('<d',self.Xmin))
        #byte 44 Bounding Box Ymin
        shp.write(struct.pack('<d',self.Ymin))
        #byte 52 Bounding Box Xmax
        shp.write(struct.pack('<d',self.Xmax))
        #byte 60 Bounding Box Ymax
        shp.write(struct.pack('<d',self.Ymax))
        #byte 68* Bounding Box Zmin
        shp.write(struct.pack('<d',self.Zmin))
        #byte 76* Bounding Box Zmax
        shp.write(struct.pack('<d',self.Zmax))
        #byte 84* Bounding Box Mmin
        shp.write(struct.pack('<d',self.Mmin))
        #byte 92* Bounding Box Mmax
        shp.write(struct.pack('<d',self.Mmax))

        #shx file header
        #byte 0, File Code
        shx.write(struct.pack('>i', self.fileCode))
        #byte 4, Unused
        shx.write(struct.pack('>i', 0))
        #byte 8, Unused
        shx.write(struct.pack('>i', 0))
        #byte 12, Unused
        shx.write(struct.pack('>i', 0))
        #byte 16, Unused
        shx.write(struct.pack('>i', 0))
        #byte 20, Unused
        shx.write(struct.pack('>i', 0))
        #byte 24, File Length, total length of file in 16-bit words
        shx.write(struct.pack('>i', 50+(4*len(self.shapes))))
        #byte 28, Version, integer
        shx.write(struct.pack('<i', self.version))
        #byte 32, shape type
        shx.write(struct.pack('<i',self.shapeType))
        #byte 36, Bounding Box Xmin
        shx.write(struct.pack('<d',self.Xmin))
        #byte 44 Bounding Box Ymin
        shx.write(struct.pack('<d',self.Ymin))
        #byte 52 Bounding Box Xmax
        shx.write(struct.pack('<d',self.Xmax))
        #byte 60 Bounding Box Ymax
        shx.write(struct.pack('<d',self.Ymax))
        #byte 68* Bounding Box Zmin
        shx.write(struct.pack('<d',self.Zmin))
        #byte 76* Bounding Box Zmax
        shx.write(struct.pack('<d',self.Zmax))
        #byte 84* Bounding Box Mmin
        shx.write(struct.pack('<d',self.Mmin))
        #byte 92* Bounding Box Mmax
        shx.write(struct.pack('<d',self.Mmax))

        #write shapes
        if self.shapeType==1:
            contentLength=10
            for id,p in enumerate(self.shapes):
                #record header
                #record numbers start at 1
                shp.write(struct.pack('>i',id+1))
                #content length
                shp.write(struct.pack('>i',contentLength))

                #record contents
                #print float(i[0]),float(i[1])
                shp.write(struct.pack('<i',self.shapeType))
            
                shp.write(struct.pack('<d',p[0]))
                shp.write(struct.pack('<d',p[1]))

                #writing index records
                #size=record header+content length
                shx.write(struct.pack('>i',50+((contentLength+4)*id)))
                shx.write(struct.pack('>i',contentLength))
                               
        elif self.shapeType==5 or self.shapeType==3:
            totalLength=50
            for id,s in enumerate(self.shapes):
                contentLength=24+(8*len(s))
                #record header
                #record numbers start at 1
                shp.write(struct.pack('>i',id+1))
                #content length
                shp.write(struct.pack('>i',contentLength))

                #record contents
                shp.write(struct.pack('<i',self.shapeType))

                #bound box for polygon
                temp=apply(zip,s)
                box=map(min,temp)+map(max,temp)
                for m in box:
                    shp.write(struct.pack('<d',m))

                #number of parts        
                shp.write(struct.pack('<i',1))
                #number of points
                shp.write(struct.pack('<i',len(s)))
                #parts index
                shp.write(struct.pack('<i',0))

                #points
                for p in s:
                    #shape type for point
                    #x coordinate
                    shp.write(struct.pack('<d',float(p[0])))
                    #y coordinate
                    shp.write(struct.pack('<d',float(p[1])))

                #writing index records
                #size=record header+content length
                shx.write(struct.pack('>i',totalLength))
                shx.write(struct.pack('>i',contentLength))
                totalLength+=contentLength+4

if __name__ == "__main__":
    #import doctest
    #print
    #doctest.testmod()
    #print
    shp = Shapefile(0)
    shp.readFile(sys.argv[1])
