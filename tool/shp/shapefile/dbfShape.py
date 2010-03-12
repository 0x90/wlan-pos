import sys
import databasefile
import shapefile

def dbfShapeFile(dbfName,xField,yField,quadrant):
    dbf=databasefile.DatabaseFile([],[],[],dbfName)
    xIndex=dbf.index(xField)
    yIndex=dbf.index(yField)
    xScale,yScale=[(1,1),(-1,1),(-1,-1),(1,-1)][quadrant-1]
    
    s=dbfShape(dbf,xIndex,yIndex,xScale,yScale)
    shp=open(dbfName[:dbfName.rfind(".")]+".shp",'wb')
    shx=open(dbfName[:dbfName.rfind(".")]+".shx",'wb')
    s.write(shp,shx)
    shp.close()
    shx.close()

def dbfShape(dbf,xIndex,yIndex,xScale=1,yScale=1):
    s=shapefile.Shapefile(1)
    for row in dbf:
        s.add([(float(row[xIndex])*xScale,float(row[yIndex])*yScale)])
    return s

if __name__=="__main__":
    dbfName=sys.argv[1]
    xField=sys.argv[2]
    yField=sys.argv[3]
    quadrant=int(sys.argv[4])
    dbfShapeFile(dbfName,xField,yField,quadrant)