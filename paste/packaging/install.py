import zipfile
import os
import urllib2
import shutil

def install_egg_file(filename, dest_dir, fileobj=None):
    """
    Install the egg file at `filename` into `dest_dir`.

    Can also be installed from a `fileobj`; if given then `filename`
    is just for error reporting.
    """
    # Since the filename may be a URL, we can't trust os.path:
    canonical_filename = filename.replace(os.sep, '/')
    # This is the convention for egg file naming:
    base_name = canonical_filename.split('/')[-1]
    package_name = base_name.split('-')[0]
    dest_dir = os.path.join(dest_dir, base_name)
    zf = zipfile.ZipFile(fileobj or filename)
    badfile = zf.testzip()
    if badfile:
        raise ValueError(
            "Zip file %s is corrupted; first bad file: %r"
            % (filename, badfile))
    for file_info in zf.infolist():
        fn = file_info.filename.lstrip('/') # make sure it's relative
        if fn.startswith('EGG-INFO/'):
            fn = package_name + '.egg-info' + fn[len('EGG-INFO'):]
        dest_fn = os.path.join(dest_dir, fn)
        if not os.path.exists(os.path.dirname(dest_fn)):
            os.makedirs(os.path.dirname(dest_fn))
        if fn.endswith('/') and not os.path.exists(dest_fn):
            os.makedir(dest_fn)
            continue
        f = open(dest_fn, 'wb')
        f.write(zf.read(file_info.filename))
        f.close()

def install_egg_from_url(url, dest_dir, package_name=None,
                         unpack=True):
    """
    Install the egg file located at `url` into `dest_dir`.  If
    `package_name` is not given, then the package name is determined
    from the url.
    """
    f = urllib2.urlopen(url)
    try:
        if unpack:
            install_egg_file(url, dest_dir, package_name=package_name,
                             fileobj=f)
        else:
            fn_out = os.path.join(dest_dir, url.split('/')[-1])
            if not os.path.exists(os.path.dirname(fn_out)):
                os.makedirs(os.path.dirname(fn_out))
            fout = open(fn_out, 'wb')
            shutil.copyfileobj(f, fout)
            fout.close()
    finally:
        f.close()
        
if __name__ == '__main__':
    import sys
    install_egg_file(*sys.argv[1:])
