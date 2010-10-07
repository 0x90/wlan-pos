#!/usr/bin/env python
import pylibkml
import csv 

def main():
    inputfile = csv.reader(file('eqs7day-M1.csv','r'), delimiter=',')
    inputfile.next() # Get rid of the header information
    Eqid = [];DateTime = [];Lat=[];Lon=[];Magnitude=[];
    Depth=[];NST=[];Location=[]
    for line in inputfile:
        Eqid.append(line[1])
        DateTime.append(line[3])
        Lat.append(line[4])
        Lon.append(line[5])
        Magnitude.append(line[6])
        Depth.append(line[7])
        NST.append(line[8])
        Location.append(line[9]) 

    libKml = pylibkml.Kml()
    KmlUtl = pylibkml.Utilities()

    icon_href = 'http://maps.google.com/mapfiles/kml/shapes/shaded_dot.png'
    iconstyleicon = libKml.create_iconstyleicon({'href': icon_href})
    iconstyle = libKml.create_iconstyle({'color':'ff0400ff', 'scale':1.2, 'colormode':'random', 'icon':iconstyleicon})

    balloon_txt = '<![CDATA[<BODY bgcolor="ffffff">\n<h3>USGS Earthquake Data'+\
      '<TABLE BORDER=1>\n'+\
      '<tr><td><b>Earthquake ID</b></td><td>$[eqid]</td></tr>\n'+\
      '<tr><td><b>Date/Time</b></td><td>$[datetime]</td></tr>\n'+\
      '<tr><td><b>Latitude,Longitude</b></td><td>$[lat],$[lon]</td></tr>\n'+\
      '<tr><td><b>Depth</b></td><td>$[depth]</td></tr>\n'+\
      '<tr><td><b>NST</b></td><td>$[nst]</td></tr>\n'+\
      '<tr><td><b>Location</b></td><td>$[location]</td></tr>\n'+\
      '</TABLE></BODY>'
    balloonstyle = libKml.create_balloonstyle({'text':balloon_txt, 'bgcolor':'ffffffff'})

    style = libKml.create_style({'id':'primary-style', 'balloonstyle':balloonstyle, 'iconstyle':iconstyle})

    placemark = []
    for i in range(0, len(Lat)):
        coordinate = libKml.create_coordinates(float(Lon[i]),float(Lat[i]))
        point = libKml.create_point({'coordinates':coordinate})

        data = []
        data.append(libKml.create_data({'name':'eqid','value':Eqid[i]}))
        data.append(libKml.create_data({'name':'datetime','value':DateTime[i]}))
        data.append(libKml.create_data({'name':'lat','value':Lat[i]}))
        data.append(libKml.create_data({'name':'lon','value':Lon[i]}))
        data.append(libKml.create_data({'name':'depth','value':Depth[i]})) 
        data.append(libKml.create_data({'name':'nst','value':NST[i]})) 
        data.append(libKml.create_data({'name':'location','value':Location[i]})) 
        extdata = libKml.create_extendeddata({'data':data})

        placemark.append(libKml.create_placemark({'name':Eqid[i], 'point':point, 
            'extendeddata':extdata, 'styleurl':'#primary-style'}))

    folder = libKml.create_folder({'name':'USGS Earthquakes', 'placemark':placemark})
    document = libKml.create_document({'folder':folder, 'style':style})

    kml = libKml.create_kml({'document':document})
    KmlFile = open('test.kml','w')
    KmlFile.write(KmlUtl.SerializePretty(kml))
    KmlFile.close()

if __name__ == '__main__':
    main()
