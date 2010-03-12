"""
Functions need to create a covex hull
"""

#utilities

def rightTurn(p1,p2,p3):
    r1,theta1=polar(p1[0],p1[1],p2[0],p2[1])
    r2,theta2=polar(p3[0],p3[1],p2[0],p2[1])

    if theta1-theta2>=math.pi:
        return True
    else:
        return False
    #return math.atan((((p2[0]-p3[0])**2+(p2[1]-p2[1])**2)**0.5)/(((p1[0]-p2[0])**2+(p1[1]-p2[1])**2)**0.5))
    #return (((p2[0] - p1[0])*(p3[1] - p1[1])) - ((p3[0] - p1[0])*(p2[1] - p1[1])))

#hull calculation

def GrahamScan(points):
    #get smallest y, choose smallest x if tie
    map(lambda x: x.reverse(),points)
    points.sort()
    map(lambda x: x.reverse(),points)    
    perimeter=[points.pop(0)]

    #sort by tangent with origin, choose smallest as second point
    points.sort(lambda a,b: cmp(rPolar(a[0],a[1],perimeter[0][0],perimeter[0][1]),rPolar(b[0],b[1],perimeter[0][0],perimeter[0][1])))
    t=Shapefile(3)
    for p in points:
        t.add([perimeter[0],p])
    t.writeFile("C:/order")
    
    perimeter.append(points.pop(0))
    points.append(perimeter[0])

    for p in points:
        if not rightTurn(perimeter[-2],perimeter[-1],p):
            perimeter.pop(-1)
            perimeter.append(p)
        else:
            perimeter.append(p)

    return perimeter       
