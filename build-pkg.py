#!/usr/bin/env python
"""
Install required third party packages for Python Paste.

Known limitations

 - Running under Windows, it must be run with Python 2.3+
   as it requires the tarfile module. On Unix/Linix platform
   will fallback to tar program.
 - Because we copy the complete SVN checkout tree of ZPTKit
   to paste/3rd-party/ZPTKit-files, due to read-only permissions
   on some svn control files, the shutil.rmtree fails. As a
   workround, delete the paste/3rd-party/ZPTKit-files/ZPTKit directory
   when running this script after a previous install.
""
import os
import sys
import errno
import urllib
import shutil

TMP="/tmp"
for tmp in ['TEMP','TMPDIR','TMP']:
    if os.environ.has_key(tmp):
        TMP = os.environ[tmp]
        break
TMP = TMP + os.sep + "tmp-build"

BASE=os.path.dirname(sys.argv[0])
if BASE == '' or BASE == ".":
    BASE = os.getcwd()

THIRD = BASE + "/paste/3rd-party"

def basename(filename, ext):
    try:
        i = filename.index(ext)
        base = filename[0:i]
    except ValueError:
        base = filename
        pass

    return base

def mkdirs(dirname, mode=0777):
    # Python Cookbook Edition 1 Recipe 4.17
    try:
        os.makedirs(dirname)
    except OSError, err:
            if err.errno != errno.EEXIST or not os.path.isdir(TMP):
                raise

def delete_pyc(arg, dirname, files):
    """
    Called by os.path.walk to delete .pyc and .pyo files
    """
    for name in files:
        if name.endswith(".pyc") or name.endswith(".pyo"):
            os.remove(os.path.join(dirname, name))

def get_file(zip_type, filename, url):
    """
    If required, download requested third party package and extract.
    On exit, the script is in the extracted package directory.
    """
    mkdirs(TMP)
    os.chdir(TMP)
    if not os.path.exists(filename):
        print "Download %s ..." % filename
        urllib.urlretrieve(url, filename)
    DIR=basename(filename, ".tar.gz")
    DIR=basename(DIR, ".tar.bz2")
    DIR=basename(DIR, ".tgz")
    if not os.path.exists(DIR):
        try:
            import tarfile
            tar = tarfile.open(filename, "r:" + zip_type)
            for file in tar.getnames():
                tar.extract(file)
        except ImportError:
            # No tarfile module, so use actual tar program
            if zip_type == "gz":
                zip_type = "z"
            else:
                zip_type = "j"
            os.system('tar fx%s "%s"' % (zip_type, filename))

    try:
        os.chdir(DIR)
    except OSError:
        pass

def installer(name):
    mkdirs(THIRD + "/" + name +"-files")
    cmd = '%s setup.py install -f --install-lib="%s/%s-files" --install-scripts="%s/%s-files/scripts" --no-compile' % (sys.executable, THIRD, name, THIRD, name)
    print cmd
    os.system(cmd)

get_file("gz","WSGI Utils-0.5.tar.gz",
        "http://www.owlfish.com/software/wsgiutils/downloads/WSGI%20Utils-0.5.tar.gz")
installer("wsgiutils")

get_file("gz", "Component-0.1.tar.gz", 
        "http://webwareforpython.org/downloads/Component-0.1.tar.gz")
DEST = THIRD + "/Component-files/Component"
mkdirs(DEST)
shutil.rmtree(DEST,ignore_errors=1)
os.chdir(THIRD)
shutil.copytree(TMP + os.sep +"Component-0.1", DEST)

zptkit_tmpdir = TMP + "/" + "ZPTKit"
if os.path.exists(zptkit_tmpdir):
    os.chdir(zptkit_tmpdir)
    cmd ="svn up"
else:
    cmd ="svn co http://svn.w4py.org/ZPTKit/trunk %s/ZPTKit" % TMP
os.system(cmd)
DEST = THIRD + "/ZPTKit-files/ZPTKit"
mkdirs(DEST)
shutil.rmtree(DEST,ignore_errors=1)
os.chdir(THIRD)
shutil.copytree(TMP + "/ZPTKit", DEST)

get_file("gz", "ZopePageTemplates-1.4.0.tar.gz", 
        "http://belnet.dl.sourceforge.net/sourceforge/zpt/ZopePageTemplates-1.4.0.tgz")
os.chdir("ZopePageTemplates")
installer("ZopePageTemplates")

get_file("gz", "scgi-1.2.tar.gz", 
        "http://www.mems-exchange.org/software/files/scgi/scgi-1.2.tar.gz")
installer("scgi")

# Do not clean up compiled python files for now
#os.path.walk(THIRD,delete_pyc,None)

sqlobject_tmpdir = TMP + "/" + "SQLObject"
if os.path.exists(sqlobject_tmpdir):
    os.chdir(sqlobject_tmpdir)
    cmd ="svn up"
else:
    cmd ="svn co http://svn.colorstudy.com/trunk/SQLObject %s/SQLObject" % TMP
os.system(cmd)
os.chdir(sqlobject_tmpdir)
installer("sqlobject")
mkdirs(THIRD + "/sqlobject-files/scripts")
shutil.copy(TMP + "/SQLObject/scripts/sqlobject-admin", 
           THIRD + "/sqlobject-files/scripts")


if not os.path.exists(TMP + "/PySourceColor.py"):
    urllib.urlretrieve("http://bellsouthpwp.net/m/e/mefjr75/python/PySourceColor.py", 
           TMP + "/PySourceColor.py")
mkdirs(THIRD + "/PySourceColor-files")
shutil.copy(TMP + "/PySourceColor.py", THIRD + "/PySourceColor-files")
