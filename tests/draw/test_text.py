"""Test how text is drawn."""

import pytest


def test_text_overflow_clip(assert_pixels):
    assert_pixels('''
        _________
        _RRRRRRR_
        _RRRRRRR_
        _________
        _RR__RRR_
        _RR__RRR_
        _________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 9px 7px;
        }
        body {
          color: red;
          font-family: weasyprint;
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


def test_text_overflow_ellipsis(assert_pixels):
    assert_pixels('''
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
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 9px 16px;
        }
        body {
          color: red;
          font-family: weasyprint;
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


def test_text_align_rtl_trailing_whitespace(assert_pixels):
    # Test text alignment for rtl text with trailing space.
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/1111
    assert_pixels('''
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
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 9px }
        body { font-family: weasyprint; color: blue; font-size: 1px }
        p { background: red; line-height: 1; width: 7em; margin: 1em }
      </style>
      <!-- &#8207 forces Unicode RTL direction for the following chars -->
      <p style="direction: rtl"> abc </p>
      <p style="direction: rtl"> &#8207;abc </p>
      <p style="direction: ltr"> abc </p>
      <p style="direction: ltr"> &#8207;abc </p>
    ''')


def test_max_lines_ellipsis(assert_pixels):
    assert_pixels('''
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
        @page {size: 10px 10px;}
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        p {
          block-ellipsis: auto;
          color: blue;
          font-family: weasyprint;
          font-size: 2px;
          max-lines: 2;
        }
      </style>
      <p>
        abcd efgh ijkl
      </p>
    ''')


@pytest.mark.xfail
def test_max_lines_nested(assert_pixels):
    assert_pixels('''
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
        @page {size: 10px 12px;}
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        div {
          continue: discard;
          font-family: weasyprint;
          font-size: 2px;
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


def test_line_clamp(assert_pixels):
    assert_pixels('''
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
        @page {size: 10px 10px;}
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        p {
          color: blue;
          font-family: weasyprint;
          font-size: 2px;
          line-clamp: 3 "(…)";
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


def test_line_clamp_none(assert_pixels):
    assert_pixels('''
        BBBB__BB__
        BBBB__BB__
        BBBB__BB__
        BBBB__BB__
        BBBB__BB__
        BBBB__BB__
        __________
        __________
        __________
        __________
    ''', '''
      <style>
        @page {size: 10px 10px;}
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        p {
          color: blue;
          font-family: weasyprint;
          font-size: 2px;
          max-lines: 1;
          continue: discard;
          block-ellipsis: "…";
          line-clamp: none;
        }
      </style>

      <p>
        aa a
        bb b
        cc c
      </p>
    ''')


def test_line_clamp_number(assert_pixels):
    assert_pixels('''
        BBBB__BB__
        BBBB__BB__
        BBBB__BB__
        BBBB__BB__
        BBBB__BBBB
        BBBB__BBBB
        __________
        __________
        __________
        __________
    ''', '''
      <style>
        @page {size: 10px 10px;}
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        p {
          color: blue;
          font-family: weasyprint;
          font-size: 2px;
          line-clamp: 3;
        }
      </style>

      <p>
        aa a
        bb b
        cc c
        dddd
        eeee
      </p>
    ''')


def test_line_clamp_nested(assert_pixels):
    assert_pixels('''
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
        @page {size: 10px 10px;}
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        div {
          color: blue;
          font-family: weasyprint;
          font-size: 2px;
          line-clamp: 3 "(…)";
        }
      </style>

      <div>
        aa a
        <p>
          bb b
          cc c
          dddd
          eeee
          ffff
          gggg
          hhhh
        </p>
      </div>
    ''')


def test_line_clamp_nested_after(assert_pixels):
    assert_pixels('''
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
        @page {size: 10px 10px;}
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        div {
          color: blue;
          font-family: weasyprint;
          font-size: 2px;
          line-clamp: 3 "(…)";
        }
      </style>

      <div>
        aa a
        <p>
          bb b
        </p>
        cc c
        dddd
        eeee
        ffff
        gggg
        hhhh
      </div>
    ''')


@pytest.mark.xfail
def test_ellipsis_nested(assert_pixels):
    assert_pixels('''
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
        @page {size: 10px 10px;}
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        div {
          block-ellipsis: auto;
          color: blue;
          continue: discard;
          font-family: weasyprint;
          font-size: 2px;
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


def test_text_align_right(assert_pixels):
    assert_pixels('''
        _________
        __RR__RR_
        __RR__RR_
        ______RR_
        ______RR_
        _________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 9px 6px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 2px;
        }
        div {
          line-height: 1;
          margin: 1px;
          text-align: right;
        }
      </style>
      <div>a c e</div>''')


def test_text_align_justify(assert_pixels):
    assert_pixels('''
        _________
        _RR___RR_
        _RR___RR_
        _RR______
        _RR______
        _________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 9px 6px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 2px;
        }
        div {
          line-height: 1;
          margin: 1px;
          text-align: justify;
        }
      </style>
      <div>a c e</div>''')


def test_text_word_spacing(assert_pixels):
    assert_pixels('''
        ___________________
        _RR____RR____RR____
        _RR____RR____RR____
        ___________________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 19px 4px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 2px;
        }
        div {
          line-height: 1;
          margin: 1px;
          word-spacing: 1em;
        }
      </style>
      <div>a c e</div>''')


def test_text_letter_spacing(assert_pixels):
    assert_pixels('''
        ___________________
        _RR____RR____RR____
        _RR____RR____RR____
        ___________________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 19px 4px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 2px;
        }
        div {
          line-height: 1;
          margin: 1px;
          letter-spacing: 2em;
        }
      </style>
      <div>ace</div>''')


def test_text_underline(assert_pixels):
    assert_pixels('''
        _____________
        _zzzzzzzzzzz_
        _zsssssssssz_
        _zsssssssssz_
        _zuuuuuuuuuz_
        _zzzzzzzzzzz_
        _____________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 13px 7px;
          margin: 2px;
        }
        body {
          color: rgba(255, 0, 0, 0.5);
          font-family: weasyprint;
          font-size: 3px;
          text-decoration: underline blue;
        }
      </style>
      <div>abc</div>''')


def test_text_overline(assert_pixels):
    # Ascent value seems to be a bit random, don’t try to get the exact
    # position of the line
    assert_pixels('''
        _____________
        _zzzzzzzzzzz_
        _zzzzzzzzzzz_
        _zsssssssssz_
        _zsssssssssz_
        _zzzzzzzzzzz_
        _____________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 13px 7px;
          margin: 2px;
        }
        body {
          color: rgba(255, 0, 0, 0.5);
          font-family: weasyprint;
          font-size: 3px;
          text-decoration: overline blue;
        }
      </style>
      <div>abc</div>''')


def test_text_line_through(assert_pixels):
    assert_pixels('''
        _____________
        _zzzzzzzzzzz_
        _zBBBBBBBBBz_
        _zuuuuuuuuuz_
        _zBBBBBBBBBz_
        _zzzzzzzzzzz_
        _____________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 13px 7px;
          margin: 2px;
        }
        body {
          color: blue;
          font-family: weasyprint;
          font-size: 3px;
          text-decoration: line-through rgba(255, 0, 0, 0.5);
        }
      </style>
      <div>abc</div>''')


def test_text_multiple_text_decoration(assert_pixels):
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/1621
    assert_pixels('''
        _____________
        _zzzzzzzzzzz_
        _zsssssssssz_
        _zBBBBBBBBBz_
        _zuuuuuuuuuz_
        _zzzzzzzzzzz_
        _____________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 13px 7px;
          margin: 2px;
        }
        body {
          color: rgba(255, 0, 0, 0.5);
          font-family: weasyprint;
          font-size: 3px;
          text-decoration: underline line-through blue;
        }
      </style>
      <div>abc</div>''')


def test_text_nested_text_decoration(assert_pixels):
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/1621
    assert_pixels('''
        _____________
        _zzzzzzzzzzz_
        _zsssssssssz_
        _zsssBBBsssz_
        _zuuuuuuuuuz_
        _zzzzzzzzzzz_
        _____________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 13px 7px;
          margin: 2px;
        }
        body {
          color: rgba(255, 0, 0, 0.5);
          font-family: weasyprint;
          font-size: 3px;
          text-decoration: underline blue;
        }
        span {
          text-decoration: line-through blue;
        }
      </style>
      <div>a<span>b</span>c</div>''')


@pytest.mark.xfail
def test_text_nested_text_decoration_color(assert_pixels):
    # See weasyprint.css.text_decoration’s TODO
    assert_pixels('''
        _____________
        _zzzzzzzzzzz_
        _zRRRRRRRRRz_
        _zRRRGGGRRRz_
        _zBBBBBBBBBz_
        _zzzzzzzzzzz_
        _____________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 13px 7px;
          margin: 2px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 3px;
          text-decoration: underline blue;
        }
        span {
          text-decoration: line-through lime;
        }
      </style>
      <div>a<span>b</span>c</div>''')


@pytest.mark.xfail
def test_text_nested_block_text_decoration(assert_pixels):
    # See weasyprint.css.text_decoration’s TODO
    assert_pixels('''
        _______
        _zzzzz_
        _zRRRz_
        _zRRRz_
        _zBBBz_
        _zRRRz_
        _zGGGz_
        _zBBBz_
        _zRRRz_
        _zRRRz_
        _zBBBz_
        _zzzzz_
        _______
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 7px 13px;
          margin: 2px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 3px;
          text-decoration: underline blue;
        }
        article {
          text-decoration: line-through lime;
        }
      </style>
      <div>a<article>b</article>c</div>''')


@pytest.mark.xfail
def test_text_float_text_decoration(assert_pixels):
    # See weasyprint.css.text_decoration’s TODO
    assert_pixels('''
        _____________
        _zzzzz_______
        _zRRRz__RRR__
        _zRRRz__RRR__
        _zBBBz__RRR__
        _zzzzz_______
        _____________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 13px 7px;
          margin: 2px;
        }
        div {
          color: red;
          font-family: weasyprint;
          font-size: 3px;
          text-decoration: underline blue;
        }
        span {
          float: right;
        }
      </style>
      <div>a<span>b</span></div>''')


def test_text_decoration_var(assert_pixels):
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/1697
    assert_pixels('''
        _____________
        _zzzzzzzzzzz_
        _zRRRRRRRRRz_
        _zBBBBBBBBBz_
        _zRRRRRRRRRz_
        _zzzzzzzzzzz_
        _____________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 13px 7px;
          margin: 2px;
        }
        body {
          --blue: blue;
          color: red;
          font-family: weasyprint;
          font-size: 3px;
          text-decoration-color: var(--blue);
          text-decoration-line: line-through;
        }
      </style>
      <div>abc</div>''')


def test_zero_width_character(assert_pixels):
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/1508
    assert_pixels('''
        ______
        _RRRR_
        _RRRR_
        ______
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 6px 4px;
          margin: 1px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 2px;
          line-height: 1;
        }
      </style>
      <div>a&zwnj;b</div>''')


def test_font_size_very_small(assert_pixels):
    assert_pixels('''
        __________
        __________
        __________
        __________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 10px 4px;
          margin: 1px;
        }
        body {
          font-family: weasyprint;
          font-size: 0.00000001px;
        }
      </style>
      test font size zero
    ''')


def test_missing_glyph_fallback(assert_pixels):
    # The apostrophe is not included in weasyprint.otf
    assert_pixels('''
        zzzzzzzzzzzzzzzzz___
        zzzzzzzzzzzzzzzzzRR_
        zzzzzzzzzzzzzzzzzRR_
        zzzzzzzzzzzzzzzzz___
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 20px 4px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 2px;
          line-height: 0;
          margin: 2px 1px;
          text-align: right;
        }
      </style>'a''')


def test_tabulation_character(assert_pixels):
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/1515
    assert_pixels('''
        __________
        _RR____RR_
        _RR____RR_
        __________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 10px 4px;
          margin: 1px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 2px;
          line-height: 1;
          tab-size: 3;
        }
      </style>
      <pre>a&Tab;b</pre>''')


def test_otb_font(assert_pixels):
    assert_pixels('''
        ____________________
        __RR______RR________
        __RR__RR__RR________
        __RR__RR__RR________
        ____________________
        ____________________
    ''', '''
      <style>
        @page {
          size: 20px 6px;
          margin: 1px;
        }
        @font-face {
          src: url(weasyprint.otb);
          font-family: weasyprint-otb;
        }
        body {
          color: red;
          font-family: weasyprint-otb;
          font-size: 4px;
          line-height: 0.8;
        }
      </style>
      AaA''')
