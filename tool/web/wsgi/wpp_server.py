#!/usr/bin/env python
# "Getting Started with WSGI" - Armin Ronacher, 2007
# http://lucumr.pocoo.org/2007/5/21/getting-started-with-wsgi
import re
import sys
from cgi import parse_qs, escape
# import the helper functions we need to get and render tracebacks
from sys import exc_info
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
#try:
#    from elementtree import ElementTree as et
#except ImportError:
#    from xml.etree import ElementTree as et
from xml.dom import minidom
from traceback import format_tb


# quick start with flask
#from flask import Flask
#app = Flask(__name__)

#@app.route("/")
#def hello():
#    return "Hello World!"

# foobar e.g 1
#def hello_world(environ, start_response):
#    parameters = parse_qs(environ.get('QUERY_STRING', ''))
#    if 'subject' in parameters:
#        subject = escape(parameters['subject'][0])
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
            e_type, e_value, tb = exc_info()
            traceback = ['Traceback (most recent call last):']
            traceback += format_tb(tb)
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
        subject = escape(args[0])
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
    #import pprint as pp
    inp = environ.get('wsgi.input','')
    content_length = environ.get('CONTENT_LENGTH', 10)
    if content_length:
        print 'content_length: ', content_length
        content_length = int(content_length)
        stream = LimitedStream(inp, content_length)
        datin = stream.read().split('?>')[1] # del xml-doc declaration.
        print datin
        #sys.exit(0)
        #xmlroot = et.parse(StringIO(datin)).getroot()
        xmldoc = minidom.parseString(datin)
        macs = xmldoc.getElementsByTagName('WLANIdentifier')[0].attributes['val'].value
        rsss = xmldoc.getElementsByTagName('WLANMatcher')[0].attributes['val'].value
        cell = ('mcc', 'mnc', 'lac', 'cid', 'rss')
        cellinfo = [xmldoc.getElementsByTagName('CellInfo')[0].attributes[item].value for item in cell]
        print 'macs: %s\nrsss: %s\ncell: %s' % (macs,rsss,cellinfo)
        xmldoc.unlink() # release dom obj.
    path = environ.get('PATH_INFO', '').lstrip('/')
    for regex, callback in urls:
        match = re.search(regex, path)
        if match is not None:
            environ['myapp.url_args'] = match.groups()
            return callback(environ, start_response)
    return not_found(environ, start_response)

# map urls to functions
urls = [
    (r'^$', index),
    (r'hello/?$', hello),
    (r'hello/(.+)$', hello)
]


if __name__ == "__main__":
    #app.run()

    # middleware
    #application = ExceptionMiddleware(application)

    from wsgiref.simple_server import make_server
    srv = make_server('localhost', 18080, application)
    srv.serve_forever()
