"""
    weasyprint.tests.test_draw.svg.test_images
    ------------------------------------------

    Test how images are drawn in SVG.

"""

from weasyprint.urls import path2url

from ...testing_utils import assert_no_logs, resource_filename
from .. import assert_pixels


@assert_no_logs
def test_image_svg():
    assert_pixels('test_image_svg', 4, 4, '''
        ____
        ____
        __B_
        ____
    ''', '''
      <style>
        @page { size: 4px 4px }
        svg { display: block }
      </style>
      <svg width="4px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <svg x="1" y="1" width="2" height="2" viewBox="0 0 10 10">
          <rect x="5" y="5" width="5" height="5" fill="blue" />
        </svg>
      </svg>
    ''')


@assert_no_logs
def test_image_image():
    assert_pixels('test_image_image', 4, 4, '''
        rBBB
        BBBB
        BBBB
        BBBB
    ''', '''
      <style>
        @page { size: 4px 4px }
        svg { display: block }
      </style>
      <svg width="4px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <image xlink:href="%s" />
      </svg>
    ''' % path2url(resource_filename('pattern.png')))
