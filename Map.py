#!/usr/bin/env python
"""
GMap: Holds all the maps and necesary html/javascript for a complete page/view. This allows you to hold more than one map per page.
Map: A map object contains map properties and a list of points.
Icon: Icon properites that can be used by your points.

A short howto:
http://lycos.dropcode.net/gregarius/Lonely_Code/2008/12/04/Google_Maps_and_Django
"""

class Icon:
    '''Get/make marker icons at http://mapki.com/index.php?title=Icon_Image_Sets'''
    def __init__(self, id='icon'):
        self.id = id
        self.image = ""             # default Google Maps icon
        self.shadow = ""
        self.iconSize = (12, 20)    # these settings match above icons
        self.shadowSize = (22, 20)
        self.iconAnchor = (6, 20)
        self.infoWindowAnchor = (5, 1)

        
class Map:
    """Basic Map class"""
    def __init__(self, id="map", pointlist=None):
        self.id      = id      # div id        
        self.width   = "500px" # map div width
        self.height  = "300px" # map div height
        self.center  = (39.9226251856,116.472770962)  # center of first view
        self.zoom    = "1"     # zoom level
        self.navctls = True    # show google map navigation controls
        self.mapctls = True    # show toogle map type (sat/map/hybrid) controls
        if pointlist == None: self.points = [] # empty point list
        else: self.points = pointlist          # supplied point list
    
    def __str__(self):
        return self.id
    
    def setpoint(self, point):
        """ Add a point (lat, long, html, icon) """
        self.points.append(point)

class GMap:
    """
    Python wrapper class for Google Maps API.
    """
    
    def __str__(self):
        return "GMap"
    
    def __init__(self, key=None, maplist=None, iconlist=None):
        """ Default values """
        if key == None:
            self.key = "ABQIAAAAQQRAsOk3uqvy3Hwwo4CclBTrVPfEE8Ms0qPwyRfPn-\
                    DOTlpaLBTvTHRCdf2V6KbzW7PZFYLT8wFD0A"      # google key
        else: self.key = key
        if maplist == None: self.maps = [ Map() ]
        else: self.maps = maplist
        if iconlist == None: self.icons = [ Icon() ]
        else: self.icons = iconlist
    
    def addicon(self, icon):
        self.icons.append(icon)
        
    def _navcontroljs(self,map):
        """ Returns the javascript for google maps control"""    
        if map.navctls:
            return  "%s%s.gmap.addControl(new GSmallMapControl());\n" % \
                ('\t'*4, map.id)
        else:
            return ""    
    
    
    def _mapcontroljs(self,map):
        """ Returns the javascript for google maps control"""    
        if map.mapctls:
            return  "%s%s.gmap.addControl(new GMapTypeControl());\n\n\
                %s.gmap.setMapType(G_SATELLITE_MAP);\n" % \
                ('\t'*4, map.id, map.id)
        else:
            return ""     
    
    
    def _mapjs(self,map):
        js = "%s_points = %s;\n" % (map.id, map.points)
        
        js = js.replace("(", "[")
        js = js.replace(")", "]")
        js = js.replace("u'", "'")
        js = js.replace("''","")    
        for icon in self.icons:
            js = js.replace("'" + icon.id + "'", icon.id)
        js += "%s var %s = new Map('%s', %s_points, %s, %s, %s);\n\n%s\n%s" % \
              ('\t'*4, map.id, map.id, map.id, map.center[0], map.center[1], map.zoom, 
               self._mapcontroljs(map), self._navcontroljs(map))
        return js
    
    
    def _iconjs(self,icon):
        js = """var %s = new GIcon(); 
                %s.image = "%s";
                %s.shadow = "%s";
                %s.iconSize = new GSize(%s, %s);
                %s.shadowSize = new GSize(%s, %s);
                %s.iconAnchor = new GPoint(%s, %s);
                %s.infoWindowAnchor = new GPoint(%s, %s); """ % \
            (icon.id, icon.id, icon.image, icon.id, icon.shadow, 
             icon.id, icon.iconSize[0], icon.iconSize[1], 
             icon.id, icon.shadowSize[0], icon.shadowSize[1], 
             icon.id, icon.iconAnchor[0], icon.iconAnchor[1], 
             icon.id, icon.infoWindowAnchor[0], icon.infoWindowAnchor[1])
        return js
     
    def _buildicons(self):
        js = ""
        if (len(self.icons) > 0):
            for icon in self.icons: js = js + self._iconjs(icon)    
        return js
    
    def _buildmaps(self):
        js = ""
        for map in self.maps: js = js + self._mapjs(map) + '\n'
        return js

    def gmapjs(self):
        """ Returns complete javacript for rendering google map """
        
        self.js = """\n<script src=\"http://maps.google.com/maps?file=api&amp;v=2&amp;key=%s\" type="text/javascript"></script>
        <script type="text/javascript">

        function load() {
            if (GBrowserIsCompatible()) {
                
            
            function Point(lat,long,html,icon) {
                  this.gpoint = new GMarker(new GLatLng(lat,long),icon);
                  this.html = html;
                  
               }               
               
               
               function Map(id,points,lat,long,zoom) {
                  this.id = id;
                  this.points = points;
                  this.gmap = new GMap2(document.getElementById(this.id));
                  this.gmap.setCenter(new GLatLng(lat, long), zoom);
                  this.markerlist = markerlist;
                  this.addmarker = addmarker;
                  this.array2points = array2points;
                   
                  function markerlist(array) {
                     for (var i in array) {
                        this.addmarker(array[i]);
                     }
                  }
                  
                  function array2points(map_points) {            
                      for (var i in map_points) {  
                        points[i] = new Point(map_points[i][0],map_points[i][1],map_points[i][2],map_points[i][3]);         }
                      return points;   
                    }                  
                  
                  function addmarker(point) {
                     if (point.html) {
                       GEvent.addListener(point.gpoint, "click", function() { // change click to mouseover or other mouse action
                           point.gpoint.openInfoWindowHtml(point.html);
                        
                       });
                       
                     }
                     this.gmap.addOverlay(point.gpoint);  
                  }
                  this.points = array2points(this.points);
                  this.markerlist(this.points);
            }  
                    %s
                    %s
            }
        }

        </script>
        
        
        """ % (self.key, self._buildicons(),self._buildmaps())
        return self.js 
    
    
        
    def genHtml(self):
        """returns a complete html page with google map(s)"""
        
        self.html = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
    <title>GMap v2</title>
    %s
  </head>

  <body onload="load()" onunload="GUnload()">
    <div id="map" style="width: 1000px; height: 600px"></div>
  </body>
</html> """ % (self.gmapjs())
        return self.html


if __name__ == "__main__":

    gmap = GMap()          # add an icon & map by default

    icon2 = Icon('icon2')  # add an extra type of icon
    icon2.image  = "kml/icons/bluedot.png" 
    icon2.shadow = "kml/icons/dotshadow.png" 
    gmap.addicon(icon2)
    print 'icon types: (img: null when default)\n%s' % ('-'*35)
    for icon in gmap.icons: 
        print 'id:\'%-5s\' img:\'%s\'' % (icon.id, icon.image)

    gmap.maps[0].zoom = 17
    point = [39.9226251856, 116.472770962, 'hello,<u>world</u>', 'icon2']     
    gmap.maps[0].setpoint(point)
    print 'maps: \n%s' % ('-'*35)
    for map in gmap.maps: print 'id:\'%-5s\'pts:\n\'%s\'' % (map.id, map.points)
    
    open('map.htm','wb').write(gmap.genHtml())   # generate test file
