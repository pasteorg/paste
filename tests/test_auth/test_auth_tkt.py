import hashlib
import six
if six.PY3:
    import base64
from paste.auth.auth_tkt import AuthTicket
try:
    from http.cookies import SimpleCookie
except ImportError:
    # Python 2
    from Cookie import SimpleCookie


def test_auth_ticket_digest_and_cookie_value():
    test_parameters = [
        (
            (
                'shared_secret',
                'username',
                '0.0.0.0',  # remote address
            ),
            {
                'tokens': ['admin'],
                'time': 1579782607
            },
            b'731274bec45f6983c1f33bac8e8baf43',
            b'731274bec45f6983c1f33bac8e8baf435e2991cfusername!admin!',
        ),
        (
            (
                'shared_secret',
                'username',
                '0.0.0.0',
            ),
            {
                'tokens': ['admin'],
                'time': 1579782607,
                'digest_algo': hashlib.sha512
            },
            b'09e72a63c57ca4cfeca5fa578646deb2b27f7a461d91ad9aa32b85c93ef6fa7744ac006eb3d9a71a36375b5ab50cbae072bb3042e2a59198b7f314900cba4423',
            b'09e72a63c57ca4cfeca5fa578646deb2b27f7a461d91ad9aa32b85c93ef6fa7744ac006eb3d9a71a36375b5ab50cbae072bb3042e2a59198b7f314900cba44235e2991cfusername!admin!',
        ),
    ]

    for test_args, test_kwargs, expected_digest, expected_cookie_value in test_parameters:
        token = AuthTicket(*test_args, **test_kwargs)
        assert expected_digest == token.digest()
        assert expected_cookie_value == token.cookie_value()


def test_auth_ticket_cookie():
    test_parameters = [
        (
            (
                'shared_secret',
                'username',
                '0.0.0.0',  # remote address
            ),
            {
                'tokens': ['admin'],
                'time': 1579782607
            },
            {
                'name': 'auth_tkt',
                'path': '/',
                'secure': '',
                'cookie_value': b'731274bec45f6983c1f33bac8e8baf435e2991cfusername!admin!'
            }
        ),
        (
            (
                'shared_secret',
                'username',
                '0.0.0.0',  # remote address
            ),
            {
                'tokens': ['admin'],
                'time': 1579782607,
                'secure': True
            },
            {
                'name': 'auth_tkt',
                'path': '/',
                'secure': 'true',
                'cookie_value': b'731274bec45f6983c1f33bac8e8baf435e2991cfusername!admin!'
            }
        ),
        (
            (
                'shared_secret',
                'username',
                '0.0.0.0',  # remote address
            ),
            {
                'tokens': ['admin'],
                'time': 1579782607,
                'cookie_name': 'custom_cookie',
                'secure': False
            },
            {
                'name': 'custom_cookie',
                'path': '/',
                'secure': '',
                'cookie_value': b'731274bec45f6983c1f33bac8e8baf435e2991cfusername!admin!'
            }
        ),
    ]

    for test_args, test_kwargs, expected_values in test_parameters:
        token = AuthTicket(*test_args, **test_kwargs)
        expected_cookie = SimpleCookie()
        if six.PY3:
            # import pdb; pdb.set_trace()
            expected_cookie_value = base64.b64encode(expected_values['cookie_value'])
        else:
            expected_cookie_value = expected_values['cookie_value'].encode('base64')

        expected_cookie[expected_values['name']] = expected_cookie_value
        expected_cookie[expected_values['name']]['path'] = expected_values['path']
        expected_cookie[expected_values['name']]['secure'] = expected_values['secure']
        assert expected_cookie == token.cookie()
