from paste.util import quoting
import unittest

class TestQuoting(unittest.TestCase):
    def test_html_unquote(self):
        self.assertEqual(quoting.html_unquote(b'&lt;hey&nbsp;you&gt;'),
                         '<hey\xa0you>')
        self.assertEqual(quoting.html_unquote(b''),
                         '')
        self.assertEqual(quoting.html_unquote(b'&blahblah;'),
                         '&blahblah;')
        self.assertEqual(quoting.html_unquote(b'\xe1\x80\xa9'),
                         '\u1029')

    def test_html_quote(self):
        self.assertEqual(quoting.html_quote(1),
                         '1')
        self.assertEqual(quoting.html_quote(None),
                         '')
        self.assertEqual(quoting.html_quote('<hey!>'),
                         '&lt;hey!&gt;')
        self.assertEqual(quoting.html_quote(b'<hey!>'),
                         b'&lt;hey!&gt;')
        self.assertEqual(quoting.html_quote('<\u1029>'),
                         '&lt;\u1029&gt;')
