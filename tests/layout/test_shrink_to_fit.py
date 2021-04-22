"""
    weasyprint.tests.layout.shrink_to_fit
    -------------------------------------

    Tests for shrink-to-fit algorithm.

"""

import pytest

from ..testing_utils import assert_no_logs, render_pages


@assert_no_logs
@pytest.mark.parametrize('margin_left', range(1, 10))
@pytest.mark.parametrize('font_size', range(1, 10))
def test_shrink_to_fit_floating_point_error_1(margin_left, font_size):
    # See bugs #325 and #288, see commit fac5ee9.
    page, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 100000px 100px }
        p { float: left; margin-left: 0.%din; font-size: 0.%dem;
            font-family: weasyprint }
      </style>
      <p>this parrot is dead</p>
    ''' % (margin_left, font_size))
    html, = page.children
    body, = html.children
    p, = body.children
    assert len(p.children) == 1


@assert_no_logs
@pytest.mark.parametrize('font_size', (1, 5, 10, 50, 100, 1000, 10000))
def test_shrink_to_fit_floating_point_error_2(font_size):
    letters = 1
    while True:
        page, = render_pages('''
          <style>
            @font-face { src: url(weasyprint.otf); font-family: weasyprint }
            @page { size: %d0pt %d0px }
            p { font-size: %dpt; font-family: weasyprint }
          </style>
          <p>mmm <b>%s a</b></p>
        ''' % (font_size, font_size, font_size, 'i' * letters))
        html, = page.children
        body, = html.children
        p, = body.children
        assert len(p.children) in (1, 2)
        assert len(p.children[0].children) == 2
        text = p.children[0].children[1].children[0].text
        assert text
        if text.endswith('i'):
            letters = 1
            break
        else:
            letters += 1
