#!/usr/bin/env python
import math
import config

def dist_on_unitshpere(lat1, long1, lat2, long2):

    # Convert latitude and longitude to 
    # spherical coordinates in radians.
    degrees_to_radians = math.pi/180.0
        
    # phi = 90 - latitude
    phi1 = (90.0 - lat1)*degrees_to_radians
    phi2 = (90.0 - lat2)*degrees_to_radians
        
    # theta = longitude
    theta = (long1-long2)*degrees_to_radians
    #theta1 = long1*degrees_to_radians
    #theta2 = long2*degrees_to_radians
        
    # Compute spherical distance from spherical coordinates.
        
    # For two locations in spherical coordinates 
    # (1, theta, phi) and (1, theta, phi)
    # cosine( arc length ) = 
    #    sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length
    
    cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta) + 
           math.cos(phi1)*math.cos(phi2))
    arc = math.acos( cos )

    # Remember to multiply arc by the radius of the earth 
    # in your favorite set of units to get length.
    return arc


if __name__ == '__main__':
    lat1, lon1, lat2, lon2 = 39.922848,116.472895, 39.922948,116.472895
    lat3, lon3, lat4, lon4 = 39.532838541666663,115.75, 39.532098524305553,115.7470920138889
    print dist_on_unitshpere(lat1, lon1, lat2, lon2)*(config.RADIUS)
    print dist_on_unitshpere(lat3, lon3, lat4, lon4)*(config.RADIUS)
