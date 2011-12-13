#!/usr/bin/env python
#coding:utf-8
import time
from gevent import monkey; monkey.patch_all()
from gevent.event import Event

from bottle import route, post, request, static_file, app
from bottle import jinja2_view as view

cache = []
new_message_event = Event()

@route('/')
@view('index')
def index():
    return {'messages': cache}

@post('/put')
def put_message():
    message = request.forms.get('message','')
    cache.append('{0} - {1}'.format(time.strftime('%m-%d %X'),message.encode('utf-8')))
    new_message_event.set()
    new_message_event.clear()
    return 'OK'

@post('/poll')
def poll_message():
    new_message_event.wait()
    return dict(data=[cache[-1]])

@route('/static/:filename', name='static')
def static_files(filename):
    return static_file(filename, root='./static/')


if __name__ == '__main__':
    import bottle
    bottle.debug(True)
    bottle.run(app=app(), host='0.0.0.0', port=5000, server='gevent')
