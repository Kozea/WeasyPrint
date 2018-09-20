"""
    weasyprint.tests.test_unicode
    -----------------------------

    Test various unicode texts and filenames.

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import os.path
import shutil
import tempfile

from ..urls import ensure_url
from .test_draw import assert_pixels_equal, document_to_pixels, html_to_pixels
from .testing_utils import FakeHTML, assert_no_logs, resource_filename


@assert_no_logs
def test_unicode():
    text = 'I løvë Unicode'
    style = '''
      @page {
        background: #fff;
        size: 200px 50px;
      }
      p { color: blue }
    '''
    _doc, expected_lines = html_to_pixels('unicode_reference', 200, 50, '''
      <style>{0}</style>
      <p><img src="pattern.png"> {1}</p>
    '''.format(style, text))

    temp = tempfile.mkdtemp(prefix=text + '-')
    try:
        stylesheet = os.path.join(temp, 'style.css')
        image = os.path.join(temp, 'pattern.png')
        html = os.path.join(temp, 'doc.html')
        with open(stylesheet, 'wb') as fd:
            fd.write(style.encode('utf8'))
        with open(resource_filename('pattern.png'), 'rb') as fd:
            image_content = fd.read()
        with open(image, 'wb') as fd:
            fd.write(image_content)
        with open(html, 'wb') as fd:
            html_content = '''
              <link rel=stylesheet href="{0}">
              <p><img src="{1}"> {2}</p>
            '''.format(
                ensure_url(stylesheet), ensure_url(image), text
            )
            fd.write(html_content.encode('utf8'))

        # TODO: change this back to actually read from a file
        document = FakeHTML(html, encoding='utf8')
        lines = document_to_pixels(document, 'unicode', 200, 50)
        assert_pixels_equal('unicode', 200, 50, lines, expected_lines)
    finally:
        shutil.rmtree(temp)
