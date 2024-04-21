# Slightly modified tests from the original cgitb test module.

# Copyright © 2001-2023 Python Software Foundation; All Rights Reserved.

import sys

import pytest

from paste.util.cgitb_hook import small, strong, grey, html, text, Hook


def test_fonts():
    text = "Hello Robbie!"
    assert small(text) == f'<small>{text}</small>'
    assert strong(text) == f'<strong>{text}</strong>'
    assert grey(text) == f'<font color="#909090">{text}</font>'


def test_blanks():
    assert small('') == ''
    assert strong('') == ''
    assert grey('') == ''


def test_html():
    try:
        raise ValueError("Hello World")
    except ValueError as err:
        # If the html was templated we could do a bit more here.
        # At least check that we get details on what we just raised.
        out = html(sys.exc_info())
        assert 'ValueError' in out
        assert str(err) in out


def test_text():
    try:
        raise ValueError("Hello World")
    except ValueError:
        out = text(sys.exc_info())
        assert 'ValueError' in out
        assert 'Hello World' in out


def dummy_error():
    raise RuntimeError("Hello World")


@pytest.mark.parametrize('format', (None, 'html', 'text'))
def test_syshook_no_logdir_default_format(format, capsys, tmp_path):
    excepthook = sys.excepthook
    args = {'logdir': tmp_path}
    if format:
        args['format'] = format
    hook = Hook(**args)
    try:
        dummy_error()
    except RuntimeError as err:
        hook(err.__class__, err, err.__traceback__)
    finally:
        sys.excepthook = excepthook

    log_files = list(tmp_path.glob('*.txt' if format == 'text' else '*.html'))
    assert len(log_files) == 1
    log_file = log_files[0]
    out = log_file.open('r').read()
    log_file.unlink()

    assert 'A problem occurred in a Python script.' in out
    assert 'RuntimeError' in out
    assert 'Hello World' in out
    assert 'test_syshook_no_logdir_default_format' in out
    if format == 'text':
        assert 'in dummy_error' in out
    else:
        assert 'in <strong>dummy_error</strong>' in out
        assert '<p>' in out
        assert '</p>' in out

    assert 'Content-Type: text/html' not in out
    assert 'contains the description of this error' not in out

    captured = capsys.readouterr()
    assert not captured.err
    output = captured.out

    if format != 'text':
        assert 'Content-Type: text/html' in output
    assert out in output
    assert log_file.name in output
    assert 'contains the description of this error' in output
