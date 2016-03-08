from paste.wsgilib import add_close


def app_iterable_func_bytes():
    yield b'a'
    yield b'b'
    yield b'c'


def app_iterable_func_unicode():
    yield b'a'.decode('ascii')
    yield b'b'.decode('ascii')
    yield b'c'.decode('ascii')


def close_func():
    global close_func_called
    close_func_called = True


def test_add_close_bytes():
    global close_func_called

    close_func_called = False
    lst = []
    app_iterable = app_iterable_func_bytes()

    obj = add_close(app_iterable, close_func)
    for x in obj:
        lst.append(x)
    obj.close()

    assert lst == [b'a', b'b', b'c']
    assert close_func_called
    assert obj._closed


def test_add_close_unicode():
    global close_func_called

    close_func_called = False
    lst = []
    app_iterable = app_iterable_func_unicode()

    obj = add_close(app_iterable, close_func)
    for x in obj:
        lst.append(x)
    obj.close()

    assert lst == ['a', 'b', 'c']
    assert close_func_called
    assert obj._closed
