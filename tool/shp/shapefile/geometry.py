"""
Geomtery functions
"""
import math


#utilities

def closedSet(x):
    """
    Returns a closed set of points by repeating the first point
    """
    return x+[x[0]]

def polarDeg(x,y):
    """
    Returns the polar coordinates of (x,y) with theta measured in degrees
    """
    r,theta=polar(x,y)
    return r,180*theta/math.pi

def polar(x,y,originX=0,originY=0):
    """
    Returns the polar coordinates of (x,y) with theta measured in radians
    """
    x=x-originX
    y=y-originY
    
    if x==0:
        if y==0:
            return(0,0)
        elif y>0:
            return (y,math.pi/2)
        else:
            return (abs(y),3*math.pi/2)
    elif x>0:
        if y==0:
            return(x,0)
        elif y>0:
            return ((x**2+y**2)**0.5,math.atan(y/x))
        else:
            return ((x**2+y**2)**0.5,(2*math.pi)+math.atan(y/x))
    else:
        if y==0:
            return (abs(x),math.pi)
        elif y>0:
            return ((x**2+y**2)**0.5,math.pi+math.atan(y/x))
        else:
            return ((x**2+y**2)**0.5,math.pi+math.atan(y/x))
        

def rPolar(x,y,originX=0,originY=0):
    """
    Returns the ploar coordinates of (x,y) in radians relative to a specified origin
    """
    r,theta=polar(x,y,originX,originY)
    return theta,r

def relative(p1,p2):
    """
    Returns coordinates for a second point based on a specified origin
    """
    return p2[0]-p1[0],p2[1]-p1[0]

#point objects

def hexagonCentroid(x,y,originX=0,originY=0,r=1):
    """
    Returns the coordinate for a hexagon centroid
    """
    if (y+2)%2:
        return (originX+((x+0.5)*r),originY-(y*r*(0.75**0.5)))
    else:
        return (originX+(x*r),originY-(y*r*(0.75**0.5)))
    
def hexagonGrid(startX,endX,startY,endY,r):
    """
    Returns a grid of hexagon centroids
    """
    deltaY=r*(0.75**0.5)
    deltaX=float(r)

    #set the orgin
    hexX=startX
    hexY=startY

    points=[]
    for y in range(startY,endY):
        if (y-startY+2)%2:
            hexX=startX+(0.5*deltaX)
        else:
            hexX=startX
        for x in range(startX,endX):
            points.append((hexX,hexY))
            hexX+=deltaX
        hexY-=deltaY

    return points

#polyline and polygon objects
def boundingBoxCoordinates(box):
    x1,x2,y1,y2=box
    return [(x1,y1),(x1,y2),(x2,y2),(x2,y1)]

def boundingBox(minX,maxX,minY,maxY):
    return [minX,maxX,minY,maxY]

def extendBoundingBox(box,x,y):
    if x<box[0]:
        box[0]=x
    elif x>box[1]:
        box[1]=x
    if y<box[2]:
        box[2]=y
    elif y>box[3]:
        box[3]=y
    return box


def rectangle(x,y,l,w):
    """
    Returns coordinates of a rectangle of height w and length l with a cornner at (x,y)
    """
    return [(x,y),(x,y+w),(x+l,y+w),(x+l,y)]

def square(x,y,l):
    """
    Returns coordinates of a square of length l with a cornner at (x,y)
    """
    return rectangle(x,y,l,l)

def segmentBuffer(x1,y1,x2,y2,r):
    """
    Returns coordinates of a rectangle along a segment or width r
    """
    x1=float(x1)
    offsetX=r*math.cos(math.atan((y1-y2)/(x1-x2)))
    offsetY=r*math.sin(math.atan((y1-y2)/(x1-x2)))
    points=[(x1-offsetX,y1+offsetY),(x2-offsetX,y2+offsetY),
            (x2+offsetX,y2-offsetY),(x1+offsetX,y1-offsetY),
            (x1-offsetX,y1+offsetY)]
    return points

def hexagon(x,y,r):
    """
    Returns coordinates of a hexagon centered at (x,y) and has a width of r
    """
    offset1=r/(3**0.5)
    offset2=r
    offset3=2*offset1
    return [(x,y+offset3),(x+offset2,y+offset1),
            (x+offset2,y-+offset1),(x,y-offset3),
            (x-offset2,y-offset1),(x-offset2,y+offset1)]


def equalLateral(x,y,r=1/(3**0.5),n=6,theta=-1*math.pi/2):
    """
    Returns the coordinates for a n-sided polygon centered at (x,y) with a radius r and rotated by theta
    """
    points=[]
    for i in range(n):
        points.append((x+(r*math.cos(-1*(theta+(i*2*math.pi/n)))),y+(r*math.sin(-1*(theta+(i*2*math.pi/n))))))
    return points  

