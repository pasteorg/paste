"""
Watches the key ``paste.httpserver.thread_pool`` to see how many
threads there are and report on any wedged threads.
"""
import string
import cgi
import time
from paste import httpexceptions
from paste.request import construct_url, parse_formvars

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
  $kill_message
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
  <td><b>$thread_id $kill</b></td>
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

kill_template = string.Template('''
 <form action="$script_name/kill" method="POST"
  style="display: inline">
  <input type="hidden" name="thread_id" value="$thread_id">
  <input type="submit" value="kill">
 </form>
''')

kill_message_template = string.Template('''
<div style="background-color: #060; color: #fff;
            border: 2px solid #000;">
  Thread $thread_id killed
</div>
''')

class WatchThreads(object):

    """
    Application that watches the threads in ``paste.httpserver``,
    showing the length each thread has been working on a request.

    If allow_kill is true, then you can kill errant threads through
    this application.

    This application can expose private information (specifically in
    the environment, like cookies), so it should be protected.
    """

    def __init__(self, allow_kill=False):
        self.allow_kill = allow_kill

    def __call__(self, environ, start_response):
        if 'paste.httpserver.thread_pool' not in environ:
            start_response('403 Forbidden', [('Content-type', 'text/plain')])
            return ['You must use the threaded Paste HTTP server to use this application']
        if environ.get('PATH_INFO') == '/kill':
            return self.kill(environ, start_response)
        else:
            return self.show(environ, start_response)

    def show(self, environ, start_response):
        start_response('200 OK', [('Content-type', 'text/html')])
        form = parse_formvars(environ)
        if form.get('kill'):
            kill_message = kill_message_template.substitute(
                thread_id=form['kill'])
        else:
            kill_message = ''
        thread_pool = environ['paste.httpserver.thread_pool']
        nworkers = thread_pool.nworkers
        now = time.time()

        workers = thread_pool.worker_tracker.items()
        workers.sort(key=lambda v: v[1][0])
        body = []
        for thread_id, (time_started, worker_environ) in workers:
            if worker_environ:
                uri = construct_url(worker_environ)
            else:
                uri = 'unknown'
            if self.allow_kill:
                kill = kill_template.substitute(
                    script_name = environ['SCRIPT_NAME'],
                    thread_id=thread_id)
            else:
                kill = ''
            thread = thread_template.substitute(
                thread_id=thread_id,
                time_html=format_time(now-time_started),
                uri=uri,
                uri_short=shorten(uri),
                environ_rows=format_environ(worker_environ),
                kill=kill,
                )
            body.append(thread)

        page = page_template.substitute(
            title="Thread Pool Worker Tracker",
            body=''.join(body),
            nworkers=nworkers,
            nworkers_used=len(workers),
            kill_message=kill_message)
        return [page]

    def kill(self, environ, start_response):
        if not self.allow_kill:
            exc = httpexceptions.HTTPForbidden(
                'Killing threads has not been enabled.  Shame on you '
                'for trying!')
            return exc(environ, start_response)
        vars = parse_formvars(environ)
        thread_id = int(vars['thread_id'])
        thread_pool = environ['paste.httpserver.thread_pool']
        if thread_id not in thread_pool.worker_tracker:
            exc = httpexceptions.PreconditionFailed(
                'You tried to kill thread %s, but it is not working on '
                'any requests' % thread_id)
            return exc(environ, start_response)
        thread_pool.kill_worker(thread_id)
        script_name = environ['SCRIPT_NAME'] or '/'
        exc = httpexceptions.HTTPFound(
            headers=[('Location', script_name+'?kill=%s' % thread_id)])
        return exc(environ, start_response)
        

hide_keys = ['paste.httpserver.thread_pool']

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

def make_watch_threads(global_conf, allow_kill=False):
    from paste.deploy.converters import asbool
    return WatchThreads(allow_kill=asbool(allow_kill))
make_watch_threads.__doc__ = WatchThreads.__doc__

def make_bad_app(global_conf, pause=0):
    def bad_app(environ, start_response):
        import thread
        if pause:
            time.sleep(pause)
        else:
            count = 0
            while 1:
                #print "I'm alive %s (%s)" % (count, thread.get_ident())
                time.sleep(10)
                count += 1
        start_response('200 OK', [('content-type', 'text/plain')])
        return 'OK, paused %s seconds' % pause
    return bad_app

