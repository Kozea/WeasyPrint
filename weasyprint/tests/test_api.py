# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""
Test the public API.

"""

import os
import contextlib
import threading
import shutil
import urlparse

from attest import Tests, assert_hook  # pylint: disable=W0611

from .testing_utils import resource_filename, assert_no_logs
from .. import HTML, CSS


SUITE = Tests()
SUITE.context(assert_no_logs)


CHDIR_LOCK = threading.Lock()

@contextlib.contextmanager
def chdir(path):
    """Change the current directory in a context manager."""
    with CHDIR_LOCK:
        old_dir = os.getcwd()
        try:
            os.chdir(path)
            yield
        finally:
            os.chdir(old_dir)


@contextlib.contextmanager
def temp_directory():
    """Context manager that gives the path to a new temporary directory.

    Remove everything on exiting the context.

    """
    directory = tempfile.mkdtemp()
    try:
        yield directory
    finally:
        shutil.rmtree(directory)


def test_resource(class_, basename, check, **kwargs):
    """Common code for testing the HTML and CSS classes."""
    absolute_filename = resource_filename(basename)
    check(class_(absolute_filename, **kwargs))
    check(class_(filename_or_url=absolute_filename, **kwargs))
    check(class_(filename=absolute_filename, **kwargs))
    check(class_(url='file://' + absolute_filename, **kwargs))
    with open(absolute_filename) as fd:
        check(class_(file_obj=fd, **kwargs))
    with open(absolute_filename) as fd:
        content = fd.read()
    with chdir(os.path.dirname(__file__)):
        relative_filename = os.path.join('resources', basename)
        check(class_(relative_filename, **kwargs))
        check(class_(string=content, base_url=relative_filename, **kwargs))
        encoding = kwargs.get('encoding') or 'utf8'
        check(class_(string=content.decode(encoding),  # unicode
                        base_url=relative_filename, **kwargs))


@SUITE.test
def test_html_parsing():
    """Test the constructor for the HTML class."""
    def check_doc1(html):
        """Check that a parsed HTML document looks like resources/doc1.html"""
        assert html.root_element.tag == 'html'
        assert [child.tag for child in html.root_element] == ['head', 'body']
        _head, body = html.root_element
        assert [child.tag for child in body] == ['h1', 'p', 'ul']
        h1 = body[0]
        assert h1.text == u'WeasyPrint test document (with Ünicōde)'
        url = urlparse.urljoin(h1.base_url, 'pattern.png')
        assert url.startswith('file:')
        assert url.endswith('weasyprint/tests/resources/pattern.png')

    test_resource(HTML, 'doc1.html', check_doc1)
    test_resource(HTML, 'doc1-utf32.html', check_doc1, encoding='utf32')


@SUITE.test
def test_css_parsing():
    """Test the constructor for the CSS class."""
    def check_css(css):
        """Check that a parsed stylsheet looks like resources/utf8-test.css"""
        # Using 'encoding' adds a CSSCharsetRule
        rule = css.stylesheet.cssRules[-1]
        assert rule.selectorText == 'h1::before'
        content, background = rule.style.getProperties(all=True)

        assert content.name == 'content'
        string, = content.propertyValue
        assert string.value == u'I løvë Unicode'

        assert background.name == 'background-image'
        url, = background.propertyValue
        url = url.absoluteUri
        assert url.startswith('file:')
        assert url.endswith('weasyprint/tests/resources/pattern.png')

    test_resource(CSS, 'utf8-test.css', check_css)
    test_resource(CSS, 'latin1-test.css', check_css, encoding='latin1')
