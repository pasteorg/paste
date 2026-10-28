import os
import pathlib
import pickle
import tempfile

import pytest

from paste import session as session_module
from paste.session import FileSession, SessionMiddleware
from paste.fixture import TestApp

info = []

def wsgi_app(environ, start_response):
    pi = environ.get('PATH_INFO', '')
    if pi in ('/get1', '/get2'):
        if pi == '/get1':
            sess = environ['paste.session.factory']()
        start_response('200 OK', [('content-type', 'text/plain')])
        if pi == '/get2':
            sess = environ['paste.session.factory']()
        if 'info' in sess:
            body = str(sess['info'])
            body = body.encode('utf8')
            return [body]
        else:
            return [b'no-info']
    if pi in ('/put1', '/put2'):
        if pi == '/put1':
            sess = environ['paste.session.factory']()
            sess['info']  = info[0]
        start_response('200 OK', [('content-type', 'text/plain')])
        if pi == '/put2':
            sess = environ['paste.session.factory']()
            sess['info']  = info[0]
        return [b'foo']

wsgi_app = SessionMiddleware(wsgi_app)

def test_app1():
    app = TestApp(wsgi_app)
    res = app.get('/get1')
    assert res.body == b'no-info'
    res = app.get('/get2')
    assert res.body ==b'no-info'
    info[:] = ['test']
    res = app.get('/put1')
    res = app.get('/get1')
    assert res.body == b'test'
    res = app.get('/get2')
    assert res.body == b'test'

def test_app2():
    app = TestApp(wsgi_app)
    info[:] = ['fluff']
    res = app.get('/put2')
    res = app.get('/get1')
    assert res.body == b'fluff'
    res = app.get('/get2')
    assert res.body == b'fluff'


# Tests for GHSA-vf89-fq68-57cx: the sid arrives from the client, so it
# selects which file FileSession reads and unpickles.

def _payload(marker):
    """A pickle that writes to ``marker`` if anything loads it."""
    class Payload:
        def __reduce__(self):
            return (pathlib.Path.write_text, (pathlib.Path(marker), 'loaded'))
    return pickle.dumps(Payload())


def _session_app(session_file_path):
    def app(environ, start_response):
        sess = environ['paste.session.factory']()
        sess['hits'] = sess.get('hits', 0) + 1
        start_response('200 OK', [('content-type', 'text/plain')])
        return [str(sess['hits']).encode('utf8')]
    return SessionMiddleware(app, session_file_path=str(session_file_path))


def test_sid_from_cookie_cannot_name_a_path(tmp_path):
    sessions = tmp_path / 'sessions'
    sessions.mkdir()
    marker = tmp_path / 'marker'
    (tmp_path / 'evil').write_bytes(_payload(marker))

    app = TestApp(_session_app(sessions))
    app.cookies['_SID_'] = '../evil'
    try:
        res = app.get('/')
    except Exception:
        # Unpatched, the payload replaces the session dict and the
        # application falls over; check the marker first either way.
        res = None

    assert not marker.exists(), 'the file named by the cookie was unpickled'
    # The bad sid is discarded and a fresh session is started instead.
    assert res is not None
    assert res.body == b'1'
    assert res.cookies_set['_SID_'] != '../evil'


def test_sid_that_is_not_a_bare_filename_is_rejected(tmp_path):
    bad = ['../evil', 'a/b', '/etc/passwd', '.', '..', 'a\\b',
           '....//evil', 'sub/../../evil', '../', './evil',
           # A colon survives ntpath.basename, and on NTFS
           # "name:stream" writes an alternate data stream of "name"
           # that no directory listing shows.
           '20261026120000-' + 'a' * 32 + ':evil', 'C:evil',
           'a*b', 'a?b', 'a"b', 'a<b', 'a>b', 'a|b', 'a\x00b', 'a\nb']
    for sid in bad:
        with pytest.raises(KeyError):
            FileSession(sid, create=False, session_file_path=str(tmp_path))
        with pytest.raises(KeyError):
            FileSession(sid, create=True, session_file_path=str(tmp_path))
    assert os.listdir(str(tmp_path)) == []
    # Not a path, just unusable; it must not escape as a ValueError.
    with pytest.raises(KeyError):
        FileSession('x' * 5000, create=False, session_file_path=str(tmp_path))


def test_ordinary_session_file_still_round_trips(tmp_path):
    app = TestApp(_session_app(tmp_path))
    assert app.get('/').body == b'1'
    assert app.get('/').body == b'2'
    sid = app.cookies['_SID_']
    assert (tmp_path / sid).exists()

    sess = FileSession(sid, create=False, session_file_path=str(tmp_path))
    assert sess.data() == {'hits': 2}


def test_session_file_written_by_older_paste_is_read(tmp_path):
    sid = '20261024120000-' + 'a' * 32
    with open(str(tmp_path / sid), 'wb') as f:
        pickle.dump({'info': 'kept'}, f)
    sess = FileSession(sid, create=False, session_file_path=str(tmp_path))
    assert sess.data() == {'info': 'kept'}


def _symlinks_work(tmp_path):
    link = tmp_path / '_probe_link'
    try:
        os.symlink(str(tmp_path), str(link))
    except (OSError, NotImplementedError, AttributeError):
        return False
    os.unlink(str(link))
    return True


def test_symlink_in_the_session_directory_is_not_followed(tmp_path):
    if not _symlinks_work(tmp_path):
        pytest.skip('symlinks not available to this account')
    sessions = tmp_path / 'sessions'
    sessions.mkdir()
    marker = tmp_path / 'marker'
    target = tmp_path / 'evil'
    target.write_bytes(_payload(marker))
    sid = '20261024120000-' + 'b' * 32
    os.symlink(str(target), str(sessions / sid))

    with pytest.raises(KeyError):
        FileSession(sid, create=False, session_file_path=str(sessions))

    # and the open itself refuses, even when the link appears after the check
    sess = FileSession(sid, create=True, session_file_path=str(sessions))
    assert sess.data() == {}
    assert not marker.exists()



def test_a_session_is_not_written_through_a_symlink(tmp_path, monkeypatch):
    # O_NOFOLLOW covers the open itself, but it does not exist on every
    # platform, so close() has to refuse as well. _O_EXTRA is cleared
    # here to stand in for such a platform.
    from paste import session as session_mod
    if not _symlinks_work(tmp_path):
        pytest.skip('symlinks not available to this account')
    sessions = tmp_path / 'sessions'
    sessions.mkdir()
    target = tmp_path / 'target'
    target.write_text('untouched')
    sid = '20261024120000-' + 'c' * 32

    sess = FileSession(sid, create=True, session_file_path=str(sessions))
    sess.data()['a'] = 1
    # the link appears between the read and the write
    os.symlink(str(target), str(sessions / sid))
    monkeypatch.setattr(session_mod, '_O_EXTRA', 0)
    with pytest.raises(OSError):
        sess.close()
    assert target.read_text() == 'untouched'


def test_quoted_cookie_value_is_still_caught(tmp_path):
    # SimpleCookie unquotes \057 to /, so the check has to run on the
    # value after cookie parsing, which is where FileSession sees it.
    sessions = tmp_path / 'sessions'
    sessions.mkdir()
    marker = tmp_path / 'marker'
    (tmp_path / 'evil').write_bytes(_payload(marker))

    app = TestApp(_session_app(sessions))
    try:
        res = app.get('/', headers={'Cookie': '_SID_="..\\057evil"'})
    except Exception:
        res = None

    assert not marker.exists()
    assert res is not None and res.body == b'1'


def test_sid_naming_a_directory_is_ignored(tmp_path):
    (tmp_path / 'adir').mkdir()
    with pytest.raises(KeyError):
        FileSession('adir', create=False, session_file_path=str(tmp_path))

    app = TestApp(_session_app(tmp_path))
    app.cookies['_SID_'] = 'adir'
    res = app.get('/')
    assert res.body == b'1'
    assert res.cookies_set['_SID_'] != 'adir'


@pytest.mark.skipif(not hasattr(os, 'mkfifo'), reason='no fifos')
def test_sid_naming_a_fifo_is_ignored(tmp_path):
    # Opening a fifo for reading blocks until someone writes to it, so
    # this is a hang, not just a wrong read.
    os.mkfifo(str(tmp_path / 'afifo'))
    with pytest.raises(KeyError):
        FileSession('afifo', create=False, session_file_path=str(tmp_path))


@pytest.mark.skipif(os.name != 'posix', reason='chmod bits are posix only')
def test_chmod_is_still_applied_to_a_new_session_file(tmp_path):
    def app(environ, start_response):
        environ['paste.session.factory']()['a'] = 1
        start_response('200 OK', [('content-type', 'text/plain')])
        return [b'ok']
    app = TestApp(SessionMiddleware(app, session_file_path=str(tmp_path),
                                    chmod='600'))
    app.get('/')
    sid = app.cookies['_SID_']
    assert oct((tmp_path / sid).stat().st_mode)[-3:] == '600'


def test_default_session_directory_is_private(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, 'gettempdir', lambda: str(tmp_path))
    path = pathlib.Path(session_module.default_session_file_path())

    assert path.parent == tmp_path
    assert path.is_dir()
    if hasattr(os, 'getuid'):
        assert str(os.getuid()) in path.name
        assert oct(path.stat().st_mode)[-3:] == '700'
    # and calling it again is happy with the directory it made
    assert session_module.default_session_file_path() == str(path)


def test_sessions_land_in_the_default_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, 'gettempdir', lambda: str(tmp_path))

    def app(environ, start_response):
        environ['paste.session.factory']()['a'] = 1
        start_response('200 OK', [('content-type', 'text/plain')])
        return [b'ok']
    testapp = TestApp(SessionMiddleware(app))
    testapp.get('/')

    path = pathlib.Path(session_module.default_session_file_path())
    assert [p.name for p in path.iterdir()] == [testapp.cookies['_SID_']]
    # nothing was written to the temp directory itself
    assert [p.name for p in tmp_path.iterdir()] == [path.name]


def test_an_explicit_session_file_path_is_left_alone(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, 'gettempdir', lambda: '/nonexistent')
    sess = FileSession('x' * 8, create=True, session_file_path=str(tmp_path))
    sess.data()['a'] = 1
    sess.close()
    assert (tmp_path / ('x' * 8)).exists()


def test_default_directory_where_modes_are_not_posix(tmp_path, monkeypatch):
    # On Windows os.mkdir ignores the mode it is given and stat reports
    # 0777 whatever the directory really allows, so the permission check
    # must not run there or it rejects the directory it just made.
    monkeypatch.setattr(tempfile, 'gettempdir', lambda: str(tmp_path))
    monkeypatch.delattr(os, 'getuid', raising=False)
    d = tmp_path / 'paste-sessions'
    d.mkdir()
    os.chmod(str(d), 0o777)
    assert session_module.default_session_file_path() == str(d)


@pytest.mark.skipif(not hasattr(os, 'getuid'), reason='posix only')
def test_a_world_writable_default_directory_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, 'gettempdir', lambda: str(tmp_path))
    (tmp_path / ('paste-sessions-%d' % os.getuid())).mkdir(mode=0o777)
    with pytest.raises(RuntimeError):
        session_module.default_session_file_path()


def test_a_symlinked_default_directory_is_refused(tmp_path, monkeypatch):
    if not _symlinks_work(tmp_path):
        pytest.skip('symlinks not available to this account')
    monkeypatch.setattr(tempfile, 'gettempdir', lambda: str(tmp_path))
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir(mode=0o700)
    name = 'paste-sessions'
    if hasattr(os, 'getuid'):
        name = '%s-%d' % (name, os.getuid())
    os.symlink(str(elsewhere), str(tmp_path / name))
    with pytest.raises(RuntimeError):
        session_module.default_session_file_path()


@pytest.mark.skipif(os.name != 'posix' or os.getuid() != 0,
                    reason='needs root to chown')
def test_a_default_directory_owned_by_someone_else_is_refused(
        tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, 'gettempdir', lambda: str(tmp_path))
    d = tmp_path / ('paste-sessions-%d' % os.getuid())
    d.mkdir(mode=0o700)
    os.chown(str(d), 65534, 65534)
    with pytest.raises(RuntimeError):
        session_module.default_session_file_path()
