import sys
import urllib2
import rfc822
import install

paste_pkg_url = 'http://pythonpaste.org/packages/info.txt'
pkg_install_url= 'http://pythonpaste.org/packages'

class PackageError(Exception):
    pass

def get_package_info(metadata_url=None):
    url = url or paste_pkg_url
    records = {}
    f = urllib2.urlopen(url)
    while 1:
        msg = rfc822.Message(f)
        if not msg:
            break
        records.setdefault(msg['Name'], []).append(msg)
    return records

def install_package(package_name, dest_dir, version=None,
                    metadata_url=None):
    all_info = get_package_info(metadata_url=metadata_url)
    if package_name not in all_info:
        raise PackageError(
            "Package %s not found" % package_name)
    available = all_info[package_name]
    package_info = None
    for info in available:
        if version is None:
            if (not package_info
                or info['Version'] > package_info['Version']):
                package_info = info
        elif version == info['Version']:
            package_info = info
            break
    if package_info is None:
        raise PackageError(
            "Version %s of Package %s not found"
            % (version, package_name))
    python_version = 'py%s.%s' % (
        sys.version_info[0], sys.version_info[1])
    package_url = (
        pkg_install_url + '/' + package_name + '-'
        + package_info['Version'] + '-' + python_version + '.egg')
    install.install_egg_from_url(package_url, dest_dir)

if __name__ == '__main__':
    print get_package_info()
    
    
