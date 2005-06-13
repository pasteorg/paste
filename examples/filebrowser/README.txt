Filebrowser Example Application
===============================

:author: Ian Bicking <ianb@colorstudy.com>

Purpose
-------

This is primarily meant as an example of using Ajax (DHTML)
development using Paste, ZPT, and Wareweb.  It's really an experiment.
It uses the `Prototype <http://prototype.conio.net/>`_ library (which
is currently distributed with the example).

I should say that I've found this library to be pleasant to work
with.  It embodies several patterns -- but not too many -- and does
them well.  I still don't understand the entire library, but what I
have used has worked well, without terrible challenges or
difficulties.  And I don't have to work too hard.

I do have my eye on making this application into something of a
framework for other filesystem-like applications, like a CMS, or a svn
browser (this uses py.path, part of the `py lib
<http://codespeak.net/py/current/doc/home.html>`_, which has an svn
backend already), or whatever.  

Status
------

This is still at an early stage.  There are almost certainly security
problems with the application (where a user can escape the root of the
application).  Lots of obviously useful functions (like add and
delete) are missing.

There's a framework kind of planned (``handlers``) for registering
different kinds of handlers with different file types.  Reading
metadata, doing editing, etc.  This hasn't been developed or used at
all yet.