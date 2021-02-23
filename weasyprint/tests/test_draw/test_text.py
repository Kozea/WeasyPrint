"""
    weasyprint.tests.test_draw.test_text
    ------------------------------------

    Test how text is drawn.

"""

import pytest

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


def test_text_align_rtl_trailing_whitespace():
    # Test text alignment for rtl text with trailing space.
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/1111
    assert_pixels('text_overflow', 9, 9, '''
        _________
        _rrrrBBB_
        _________
        _rrrrBBB_
        _________
        _BBBrrrr_
        _________
        _BBBrrrr_
        _________
    ''', '''
      <style>
        @font-face {src: url(AHEM____.TTF); font-family: ahem}
        @page { background: white; size: 9px }
        body { font-family: ahem; color: blue; font-size: 1px }
        p { background: red; line-height: 1; width: 7em; margin: 1em }
      </style>
      <!-- &#8207 forces Unicode RTL direction for the following chars -->
      <p style="direction: rtl"> abc </p>
      <p style="direction: rtl"> &#8207;abc </p>
      <p style="direction: ltr"> abc </p>
      <p style="direction: ltr"> &#8207;abc </p>
    ''')


def test_max_lines_ellipsis():
    assert_pixels('max_lines_ellipsis', 10, 10, '''
        BBBBBBBB__
        BBBBBBBB__
        BBBBBBBBBB
        BBBBBBBBBB
        __________
        __________
        __________
        __________
        __________
        __________
    ''', '''
      <style>
        @page {size: 10px 10px; background: white}
        @font-face {src: url(AHEM____.TTF); font-family: ahem}
        p {
          block-ellipsis: auto;
          color: blue;
          font-family: ahem;
          font-size: 2px;
          line-height: 1;
          max-lines: 2;
        }
      </style>
      <p>
        abcd efgh ijkl
      </p>
    ''')


@pytest.mark.xfail
def test_max_lines_nested():
    assert_pixels('max_lines_nested', 10, 12, '''
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        rrrrrrrrrr
        rrrrrrrrrr
        rrrrrrrrrr
        rrrrrrrrrr
        BBBBBBBBBB
        BBBBBBBBBB
        __________
        __________
    ''', '''
      <style>
        @page {size: 10px 12px; background: white}
        @font-face {src: url(AHEM____.TTF); font-family: ahem}
        div {
          continue: discard;
          font-family: ahem;
          font-size: 2px;
          line-height: 1;
        }
        #a {
          color: blue;
          max-lines: 5;
        }
        #b {
          color: red
          max-lines: 2;
        }
      </style>
      <div id=a>
        aaaaa
        aaaaa
        <div id=b>
          bbbbb
          bbbbb
          bbbbb
          bbbbb
        </div>
        aaaaa
        aaaaa
      </div>
    ''')


def test_line_clamp():
    assert_pixels('line_clamp', 10, 10, '''
        BBBB__BB__
        BBBB__BB__
        BBBB__BB__
        BBBB__BB__
        BBBBBBBBBB
        BBBBBBBBBB
        __________
        __________
        __________
        __________
    ''', '''
      <style>
        @page {size: 10px 10px; background: white}
        @font-face {src: url(AHEM____.TTF); font-family: ahem}
        p {
          color: blue;
          font-family: ahem;
          font-size: 2px;
          line-clamp: 3 "(…)";
          line-height: 1;
        }
      </style>

      <p>
        aa a
        bb b
        cc c
        dddd
        eeee
        ffff
        gggg
        hhhh
      </p>
    ''')


@pytest.mark.xfail
def test_ellipsis_nested():
    assert_pixels('ellipsis_nested', 10, 10, '''
        BBBBBB____
        BBBBBB____
        BBBBBB____
        BBBBBB____
        BBBBBB____
        BBBBBB____
        BBBBBB____
        BBBBBB____
        BBBBBBBB__
        BBBBBBBB__
    ''', '''
      <style>
        @page {size: 10px 10px; background: white}
        @font-face {src: url(AHEM____.TTF); font-family: ahem}
        div {
          block-ellipsis: auto;
          color: blue;
          continue: discard;
          font-family: ahem;
          font-size: 2px;
          line-height: 1;
        }
      </style>
      <div>
        <p>aaa</p>
        <p>aaa</p>
        <p>aaa</p>
        <p>aaa</p>
        <p>aaa</p>
        <p>aaa</p>
      </div>
    ''')
