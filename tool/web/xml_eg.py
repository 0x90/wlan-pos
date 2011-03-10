#!/usr/bin/env python
# -*- coding: UTF-8  -*-
import os
import xml.etree.ElementTree as et
 
def load_xml_file(filename):
    root = et.parse(filename).getroot()
    intro = root.find('intro').text
    print intro
    all_users = root.findall('list')
    for user in all_users:
        head = user.find('head').text
        name = user.find('name').text
        sex = user.find('sex').text
        print head,name,sex
 
if __name__ == '__main__':
 
    workpath = os.getcwd()
    load_xml_file(r'%s/eg.xml' % workpath)
