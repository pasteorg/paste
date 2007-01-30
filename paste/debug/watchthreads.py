"""
Watches the key ``paste.httpserver.worker_tracker`` to see how many
threads there are and report on any wedged threads.
"""
import string
import cgi
import time
from paste.request import construct_url

page_template = string.Template('''
<html>
 <head>
  <style type="text/css">
   body {
     font-family: sans-serif;
   }
   table.environ tr td {
     border-bottom: #bbb 1px solid;
   }
   table.thread {
     border: 1px solid #000;
     margin-bottom: 1em;
   }
   table.thread tr td {
     border-bottom: #999 1px solid;
     padding-right: 1em;
   }
  </style>
  <title>$title</title>
 </head>
 <body>
  <h1>$title</h1>
  <div>Pool size: $nworkers
       ($nworkers_used used including current request)</div>
  $body
 </body>
</html>
''')

thread_template = string.Template('''
<table class="thread">
 <tr>
  <td><b>Thread</b></td>
  <td><b>$thread_id</b></td>
 </tr>
 <tr>
  <td>Time processing request</td>
  <td>$time_html</td>
 </tr>
 <tr>
  <td>URI</td>
  <td><a href="$uri">$uri_short</a></td>
 <tr>
  <td colspan="2">
   <a href="#"
      onclick="
        var el = document.getElementById('environ');
        if (el.style.display) {
            el.style.display = '';
            this.innerHTML = 'Hide environ';
        } else {
            el.style.display = 'none';
            this.innerHTML = 'Show environ';
        }
        return false
      ">Show environ</a>
   
   <div id="environ" style="display: none">
    <table class="environ">
     $environ_rows
    </table>
   </div>
  </td>
 </tr>
</table>
''')

environ_template = string.Template('''
 <tr>
  <td>$key</td>
  <td>$value</td>
 </tr>
''')

def watch_threads(environ, start_response):
    start_response('200 OK', [('Content-type', 'text/html')])
    if 'paste.httpserver.worker_tracker' not in environ:
        return ['You must use the threaded Paste HTTP server to use this application']
    worker_tracker = environ['paste.httpserver.worker_tracker']
    nworkers = environ['paste.httpserver.nworkers']
    now = time.time()
    
    workers = worker_tracker.items()
    workers.sort(key=lambda v: v[1][0])
    body = []
    for thread_id, (time_started, worker_environ) in workers:
        if worker_environ:
            uri = construct_url(worker_environ)
        else:
            uri = 'unknown'
        thread = thread_template.substitute(
            thread_id=thread_id,
            time_html=format_time(now-time_started),
            uri=uri,
            uri_short=shorten(uri),
            environ_rows=format_environ(worker_environ),
            )
        body.append(thread)
    
    page = page_template.substitute(
        title="Thread Pool Worker Tracker",
        body=''.join(body),
        nworkers=nworkers,
        nworkers_used=len(workers))
    return [page]

hide_keys = ['paste.httpserver.worker_tracker']

def format_environ(environ):
    if environ is None:
        return environ_template.substitute(
            key='---',
            value='No environment registered for this thread yet')
    environ_rows = []
    for key, value in sorted(environ.items()):
        if key in hide_keys:
            continue
        try:
            if key.upper() != key:
                value = repr(value)
            environ_rows.append(
                environ_template.substitute(
                key=cgi.escape(str(key)),
                value=cgi.escape(str(value))))
        except Exception, e:
            environ_rows.append(
                environ_template.substitute(
                key=cgi.escape(str(key)),
                value='Error in <code>repr()</code>: %s' % e))
    return ''.join(environ_rows)
    
def format_time(time_length):
    if time_length < 1:
        return '%0.2fsec' % time_length
    elif time_length < 60:
        return '<span style="color: #900">%.1fsec</span>' % time_length
    else:
        return '<span style="background-color: #600; color: #fff">%isec</span>' % time_length

def shorten(s):
    if len(s) > 60:
        return s[:40]+'...'+s[-10:]
    else:
        return s

def make_watch_threads(global_conf):
    return watch_threads

def make_bad_app(global_conf, pause=0):
    def bad_app(environ, start_response):
        if pause:
            time.sleep(pause)
        else:
            while 1:
                time.sleep(10000)
        start_response('200 OK', [('content-type', 'text/plain')])
        return 'OK, paused %s seconds' % pause
    return bad_app

