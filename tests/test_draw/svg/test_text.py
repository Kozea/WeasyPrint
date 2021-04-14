"""
    weasyprint.tests.test_draw.svg.test_text
    ----------------------------------------

    Test how SVG text is drawn.

"""

from ...testing_utils import assert_no_logs
from .. import assert_pixels


@assert_no_logs
def test_text_fill():
    assert_pixels('text_fill', 20, 6, '''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
        ____________________
        ____________________
        ____________________
        ____________________
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 6px }
        svg { display: block }
      </style>
      <svg width="20px" height="6px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="2" font-family="weasyprint" font-size="2" fill="blue">
          ABC DEF
        </text>
      </svg>
    ''')
