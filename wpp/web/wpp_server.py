#!/usr/bin/env python
# "Getting Started with WSGI" - Armin Ronacher, 2007, 
# http://lucumr.pocoo.org/2007/5/21/getting-started-with-wsgi.
import re
import sys
import os
import cgi
#import time
#import datetime as dt
# import the helper functions we need to get and render tracebacks
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
#from xml.dom.minidom import parseString as xmlparser
from lxml.etree import fromstring as xmlparser
from wsgiref import simple_server
import traceback as tb
import numpy as np

import online as wlanpos
import config as cfg
from offline import getIP


# quick start with flask
#from flask import Flask
#app = Flask(__name__)

#@app.route("/")
#def hello():
#    return "Hello World!"

# foobar e.g 1
#def hello_world(environ, start_response):
#    parameters = cgi.parse_qs(environ.get('QUERY_STRING', ''))
#    if 'subject' in parameters:
#        subject = cgi.escape(parameters['subject'][0])
#    else:
#        subject = 'World'
#    start_response('200 OK', [('Content-Type', 'text/html')])
#    return ['''Hello %(subject)s!''' % {'subject': subject}]


class ExceptionMiddleware(object):
    """The middleware we use."""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        """Call the application can catch exceptions."""
        appiter = None
        # just call the application and send the output back
        # unchanged but catch exceptions
        try:
            appiter = self.app(environ, start_response)
            for item in appiter:
                yield item
        # if an exception occours we get the exception information
        # and prepare a traceback we can render
        except:
            e_type, e_value, tb = sys.exc_info()
            traceback = ['Traceback (most recent call last):']
            traceback += tb.format_tb(tb)
            traceback.append('%s: %s' % (e_type.__name__, e_value))
            # we might have not a stated response by now. try
            # to start one with the status code 500 or ignore an
            # raised exception if the application already started one.
            try:
                start_response('500 INTERNAL SERVER ERROR', [
                               ('Content-Type', 'text/plain')])
            except:
                pass
            yield '\n'.join(traceback)

        # wsgi applications might have a close function. If it exists
        # it *must* be called.
        if hasattr(appiter, 'close'):
            appiter.close()


class LimitedStream(object):
    '''
    LimitedStream wraps another stream in order to not allow reading from it
    past specified amount of bytes.
    '''
    def __init__(self, stream, limit, buf_size=64 * 1024 * 1024):
        self.stream = stream
        self.remaining = limit
        self.buffer = ''
        self.buf_size = buf_size

    def _read_limited(self, size=None):
        if size is None or size > self.remaining:
            size = self.remaining
        if size == 0:
            return ''
        result = self.stream.read(size)
        self.remaining -= len(result)
        return result

    def read(self, size=None):
        if size is None:
            result = self.buffer + self._read_limited()
            self.buffer = ''
        elif size < len(self.buffer):
            result = self.buffer[:size]
            self.buffer = self.buffer[size:]
        else: # size >= len(self.buffer)
            result = self.buffer + self._read_limited(size - len(self.buffer))
            self.buffer = ''
        return result

    def readline(self, size=None):
        while '\n' not in self.buffer and \
              (size is None or len(self.buffer) < size):
            if size:
                # since size is not None here, len(self.buffer) < size
                chunk = self._read_limited(size - len(self.buffer))
            else:
                chunk = self._read_limited()
            if not chunk:
                break
            self.buffer += chunk
        sio = StringIO(self.buffer)
        if size:
            line = sio.readline(size)
        else:
            line = sio.readline()
        self.buffer = sio.read()
        return line

def hgweb_handler(environ, start_response):
    from mercurial import demandimport; demandimport.enable()
    #from mercurial.hgweb.hgwebdir_mod import hgwebdir
    #from mercurial.hgweb.request import wsgiapplication
    from mercurial.hgweb import hgweb
     
    hgweb_conf = '/etc/mercurial/hgweb.conf'
    #make_web_app = hgwebdir(hgweb_conf)
    hg_webapp = hgweb(hgweb_conf)
     
    #hg_webapp = wsgiapplication(make_web_app)
    return hg_webapp(environ, start_response)

def index(environ, start_response):
    """This function will be mounted on "/" and display a link
    to the hello world page."""
    start_response('200 OK', [('Content-Type', 'text/html')])
    return ['''Hello World Application, This is the Hello World application: 
               continue 'hello/\'''']

def hello(environ, start_response):
    """Like the example above, but it uses the name specified in the URL."""
    # get the name from the url if it was specified there.
    args = environ['myapp.url_args']
    if args:
        subject = cgi.escape(args[0])
    else:
        subject = 'World'
    start_response('200 OK', [('Content-Type', 'text/html')])
    return ['''Hello %(subject)s, 
               Good to see u %(subject)s!''' % {'subject': subject}]

def not_found(environ, start_response):
    """Called if no URL matches."""
    start_response('404 NOT FOUND', [('Content-Type', 'text/plain')])
    return ['Not Found']

def application(environ, start_response):
    """
    The main WSGI application. Dispatch the current request to
    the functions from above and store the regular expression
    captures in the WSGI environment as  `myapp.url_args` so that
    the functions from above can access the url placeholders.

    If nothing matches call the `not_found` function.
    """
    # test code for speed.
    #t = dt.datetime.now()
    #print 'time(s-ms) --> %s-%s' % (t.second, t.microsecond)
    path = environ.get('PATH_INFO', '').lstrip('/')
    for regex, callback in urls:
        match = re.search(regex, path)
        if match is not None:
            print regex, callback
            environ['myapp.url_args'] = match.groups()
            return callback(environ, start_response)
    return not_found(environ, start_response)

def wpp_handler(environ, start_response):
    """WPP posreq handler"""
    # get the name from the url if it was specified there.
    #args = environ['myapp.url_args']
    #if args:
    #    subject = cgi.escape(args[0])
    #else:
    #    subject = 'distribution'
    inp = environ.get('wsgi.input','')
    content_length = environ.get('CONTENT_LENGTH', 10)
    if content_length:
        #t = dt.datetime.now()
        #print 'start time(s-ms) --> %s-%s' % (t.second, t.microsecond)
        stream = LimitedStream(inp, int(content_length))
        datin = stream.read()
        if not datin: sys.exit(99)
        datin = datin.split('dtd">')
        if len(datin) == 1: # del xml-doc declaration.
            datin = datin[0].split('?>')
            if len(datin) == 1: datin = datin[0]
            else: datin = datin[1] 
        else: datin = datin[1] # del xml-doc declaration.
        print datin
        xmldoc = xmlparser(datin)
        # xml.dom.minidom solution.
        #macs = xmldoc.getElementsByTagName('WLANIdentifier')[0].attributes['val'].value.split('|')
        #rsss = xmldoc.getElementsByTagName('WLANMatcher')[0].attributes['val'].value.split('|')
        #xmldoc.unlink() # release dom obj.
        # lxml solution.
        #macs, rsss = [ v['val'].split('|') for v in [t.attrib for t in xmldoc.iter()][-2:] ]
        macs, rsss = [ child.attrib['val'].split('|') for child in xmldoc.getchildren()[-2:] ]
        #t = dt.datetime.now()
        #print 'parse time(s-ms) --> %s-%s' % (t.second, t.microsecond)
        macs = np.array(macs)
        rsss = np.array(rsss)
        XHTML_IMT = "application/xhtml+xml"
        # fix postion.
        num_visAPs = len(macs)
        INTERSET = min(cfg.CLUSTERKEYSIZE, num_visAPs)
        idxs_max = np.argsort(rsss)[:INTERSET]
        mr = np.vstack((macs, rsss))[:,idxs_max]
        loc = wlanpos.fixPos(INTERSET, mr, verb=False)
        #loc = [39.895167306122453, 116.34509951020408, 24.660629537376867]
        # write PosRes xml.
        if loc:
            lat, lon, ee = loc
            errinfo='OK' 
            errcode='100'
        else:
            lat = 39.9055
            lon = 116.3914
            ee = 1000
            errinfo = 'AccuTooBad'
            errcode = '102'
        pos_resp="""<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE PosRes SYSTEM "PosRes.dtd">
        <PosRes>
                <Result ErrCode="%s" ErrDesc="%s"/>
                <Coord lat="%.6f" lon="%.6f" h="0.0"/>
                <ErrRange val="%.2f"/>
        </PosRes>""" % (errcode, errinfo, lat, lon, ee)
        contlen = len(pos_resp)
        start_response('200 OK', [('Content-Type', XHTML_IMT),('Content-Length', str(contlen))])
        print pos_resp
        #t = dt.datetime.now()
        #print 'end time(s-ms) --> %s-%s' % (t.second, t.microsecond)
        print '='*30
        return [ pos_resp ]
    else:
        return not_found(environ, start_response)

# map urls to functions
urls = [
    #(r'^$', index),
    (r'wlan/distribution$', wpp_handler),
    #(r'wlan/hg$', hgweb_handler),
    #(r'hello/?$', hello),
    #(r'hello/(.+)$', hello),
]


class PimpedWSGIServer(simple_server.WSGIServer):
    # To increase the backlog
    request_queue_size = 500

 
class PimpedHandler(simple_server.WSGIRequestHandler):
    # to disable logging
    def log_message(self, *args):
        pass


if __name__ == "__main__":
    try:
        import psyco
        psyco.bind(wpp_handler)
        psyco.bind(application)
        #psyco.full()
        #psyco.log()
        #psyco.profile(0.3)
    except ImportError:
        pass

    #app.run()

    # middleware
    #application = ExceptionMiddleware(application)

    port = 8080

    # wsgiref server from python stdlib.
    #httpd = PimpedWSGIServer(('',port), PimpedHandler)
    #httpd.set_app(wpp_handler)
    # Gevent server.
    #from gevent.wsgi import WSGIServer
    #httpd = WSGIServer(('', port), wpp_handler, spawn=None)
    #httpd.backlog = 256
    #httpd.log = False
    # Meinheld server.
    from meinheld import server
    server.listen(("0.0.0.0", 8080))
    # Bjoern server.
    #import bjoern
    #bjoern.listen(wpp_handler, '0.0.0.0', port)
    # FIXME: Fapws4 server.
    #import fapws._evwsgi as evwsgi
    #from fapws import base
    #evwsgi.start('0.0.0.0', '8080') 
    #evwsgi.set_base_module(base)
    #evwsgi.wsgi_cb(('/wlan', wpp_handler))
    #evwsgi.set_debug(0)	   
    # Gunicorn 
    # $gunicorn -b :8080 -w 5 wpp_server:wpp_handler
    # $gunicorn -b :8080 -w 5 -k "egg:meinheld#gunicorn_worker" wpp_server:wpp_handler
    # $gunicorn -b :8080 -w 5 -k "egg:gunicorn#gevent" wpp_server:wpp_handler
    # $gunicorn -b :8080 -w 5 -k "egg:gevent#gunicorn_worker" wpp_server:wpp_handler

    
    # Get IP address.
    ipaddr = getIP()
    if 'wlan0' in ipaddr:
        ipaddr = ipaddr['wlan0']
    else:
        ipaddr = ipaddr['eth0']
    #httpd = simple_server.make_server(ipaddr, port, application)
    print 'Starting up HTTP server on %s:%d ...' % (ipaddr, port)

    # Respond to requests until process is killed
    #httpd.serve_forever() # wsgiref, Gevent
    #bjoern.run() # bjoern
    server.run(wpp_handler) # Meinheld
    #evwsgi.run() # Fapws3
