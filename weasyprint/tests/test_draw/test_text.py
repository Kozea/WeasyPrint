"""
    weasyprint.tests.test_draw.test_text
    ------------------------------------

    Test how text is drawn.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from . import assert_pixels


def test_text_overflow_clip():
    assert_pixels('text_overflow', 9, 7, '''
        _________
        _RRRRRRR_
        _RRRRRRR_
        _________
        _RR__RRR_
        _RR__RRR_
        _________
    ''', '''
      <style>
        @font-face {src: url(AHEM____.TTF); font-family: ahem}
        @page {
          size: 9px 7px;
          background: white;
        }
        body {
          color: red;
          font-family: ahem;
          font-size: 2px;
        }
        div {
          line-height: 1;
          margin: 1px;
          overflow: hidden;
          width: 3.5em;
        }
      </style>
      <div>abcde</div>
      <div style="white-space: nowrap">a bcde</div>''')


def test_text_overflow_ellipsis():
    assert_pixels('text_overflow', 9, 16, '''
        _________
        _RRRRRR__
        _RRRRRR__
        _________
        _RR__RR__
        _RR__RR__
        _________
        _RRRRRR__
        _RRRRRR__
        _________
        _RRRRRRR_
        _RRRRRRR_
        _________
        _RRRRRRR_
        _RRRRRRR_
        _________
    ''', '''
      <style>
        @font-face {src: url(AHEM____.TTF); font-family: ahem}
        @page {
          background: white;
          size: 9px 16px;
        }
        body {
          color: red;
          font-family: ahem;
          font-size: 2px;
        }
        div {
          line-height: 1;
          margin: 1px;
          overflow: hidden;
          text-overflow: ellipsis;
          width: 3.5em;
        }
        div div {
          margin: 0;
        }
      </style>
      <div>abcde</div>
      <div style="white-space: nowrap">a bcde</div>
      <div><span>a<span>b</span>cd</span>e</div>
      <div><div style="text-overflow: clip">abcde</div></div>
      <div><div style="overflow: visible">abcde</div></div>
''')
