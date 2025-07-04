"""Test how text is drawn."""

import pytest

from ..testing_utils import SANS_FONTS


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
    # Regression test for #1111.
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


def test_rtl_default_direction(assert_pixels):
    assert_pixels('''
        _____BBBBB_____
        _____BBBBB_____
        _____BBBBB_____
        _____BBBBB_____
        BBBBBBBBBB_____
    ''', '''
      <style>
        @page { size: 15px 5px }
        body { font-family: weasyprint; color: blue; font-size: 5px; line-height: 1 }
      </style>
      اب
    ''')


def test_rtl_forced_direction(assert_pixels):
    assert_pixels('''
        __________BBBBB
        __________BBBBB
        __________BBBBB
        __________BBBBB
        _____BBBBBBBBBB
    ''', '''
      <style>
        @page { size: 15px 5px }
        body { font-family: weasyprint; color: blue; font-size: 5px; line-height: 1 }
      </style>
      <div style="direction: rtl">اب</div>
    ''')


def test_rtl_nested_inline(assert_pixels):
    assert_pixels('''
        RRRRR________________BBBBB___________RRRRR___________BBBBB
        RRRRR________________BBBBB___________RRRRR___________BBBBB
        RRRRR________________BBBBB___________RRRRR___________BBBBB
        RRRRR________________BBBBB___________RRRRR___________BBBBB
        RRRRRRRRRR______BBBBBBBBBB______RRRRRRRRRR______BBBBBBBBBB
        ______________________________________BBBBB__________RRRRR
        ______________________________________BBBBB__________RRRRR
        ______________________________________BBBBB__________RRRRR
        ______________________________________BBBBB__________RRRRR
        _________________________________BBBBBBBBBB_____RRRRRRRRRR
    ''', '''
      <style>
        @page { size: 58px 10px }
        body { font-family: weasyprint; color: blue; font-size: 5px; line-height: 1 }
        span { color: red }
      </style>
      <div style="direction: rtl; text-align: justify">
        اب <span>اب</span> اب <span>با اب</span> اب
      </div>
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


def test_text_align_justify_nbsp(assert_pixels):
    assert_pixels('''
        ___________________
        _RR___RR___RR___RR_
        _RR___RR___RR___RR_
        ___________________
    ''', '''
      <style>
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
          text-align: justify-all;
        }
      </style>
      <div>a b&nbsp;c&nbsp;d</div>''')


def test_text_word_spacing(assert_pixels):
    assert_pixels('''
        ___________________
        _RR____RR____RR____
        _RR____RR____RR____
        ___________________
    ''', '''
      <style>
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


def test_text_underline_offset(assert_pixels):
    assert_pixels('''
        _____________
        _zzzzzzzzzzz_
        _zRRRRRRRRRz_
        _zRRRRRRRRRz_
        _zzzzzzzzzzz_
        _zzzzzzzzzzz_
        _zBBBBBBBBBz_
        _zzzzzzzzzzz_
        _____________
    ''', '''
      <style>
        @page {
          size: 13px 9px;
          margin: 2px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 3px;
          text-decoration: underline blue;
          text-underline-offset: 2px;
        }
      </style>
      <div>abc</div>''')


def test_text_underline_offset_percentage(assert_pixels):
    assert_pixels('''
        _____________
        _zzzzzzzzzzz_
        _zRRRRRRRRRz_
        _zRRRRRRRRRz_
        _zzzzzzzzzzz_
        _zzzzzzzzzzz_
        _zBBBBBBBBBz_
        _zzzzzzzzzzz_
        _____________
    ''', '''
      <style>
        @page {
          size: 13px 9px;
          margin: 2px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 3px;
          text-decoration: underline blue;
          text-underline-offset: 70%;
        }
      </style>
      <div>abc</div>''')


def test_text_underline_thickness(assert_pixels):
    assert_pixels('''
        _____________
        _zzzzzzzzzzz_
        _zRRRRRRRRRz_
        _zRRRRRRRRRz_
        _zzzzzzzzzzz_
        _zzzzzzzzzzz_
        _zBBBBBBBBBz_
        _zBBBBBBBBBz_
        _zzzzzzzzzzz_
    ''', '''
      <style>
        @page {
          size: 13px 9px;
          margin: 2px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 3px;
          text-decoration: underline blue 3px;
          text-underline-offset: 2px;
        }
      </style>
      <div>abc</div>''')


def test_text_underline_thickness_percentage(assert_pixels):
    assert_pixels('''
        _____________
        _zzzzzzzzzzz_
        _zRRRRRRRRRz_
        _zRRRRRRRRRz_
        _zzzzzzzzzzz_
        _zzzzzzzzzzz_
        _zBBBBBBBBBz_
        _zBBBBBBBBBz_
        _zzzzzzzzzzz_
    ''', '''
      <style>
        @page {
          size: 13px 9px;
          margin: 2px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 3px;
          text-decoration: underline blue 100%;
          text-underline-offset: 2px;
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
    # Regression test for #1621.
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
    # Regression test for #1621.
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
    # Regression test for #1697.
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
    # Regression test for #1508.
    assert_pixels('''
        ______
        _RRRR_
        _RRRR_
        ______
    ''', '''
      <style>
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
        ___zzzzzzzzzzzzzzzzz
        _RRzzzzzzzzzzzzzzzzz
        _RRzzzzzzzzzzzzzzzzz
        ___zzzzzzzzzzzzzzzzz
    ''', '''
      <style>
        @page {
          size: 20px 4px;
        }
        body {
          color: red;
          font-family: weasyprint, %s;
          font-size: 2px;
          line-height: 0;
          margin: 2px 1px;
        }
      </style>a\'''' % SANS_FONTS)


def test_tabulation_character(assert_pixels):
    # Regression test for #1515.
    assert_pixels('''
        __________
        _RR____RR_
        _RR____RR_
        __________
    ''', '''
      <style>
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


def test_huge_justification(assert_pixels):
    # Regression test for #2262.
    assert_pixels('''
        ____
        _RR_
        _RR_
        ____
    ''', '''
      <style>
        @page {
          size: 4px 4px;
          margin: 1px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 2px;
          line-height: 1;
          text-align: justify-all;
          width: 100000px;
        }
      </style>
      A B''')


def test_font_variant_caps_small(assert_pixels):
    assert_pixels('''
        ________
        _BB_BB__
        _BB_B_B_
        _B__BB__
        _B__B___
        ________
    ''', '''
      <style>
        @page {size: 8px 6px}
        p {
          color: blue;
          font-variant-caps: small-caps;
          font-family: %s;
          font-size: 6px;
          line-height: 1;
        }
      </style>
      <p>Pp</p>
    ''' % SANS_FONTS)


def test_font_variant_caps_all_small(assert_pixels):
    assert_pixels('''
        ________
        BB_BB___
        B_BB_B__
        BB_BB___
        B__B____
        ________
    ''', '''
      <style>
        @page {size: 8px 6px}
        p {
          color: blue;
          font-variant-caps: all-small-caps;
          font-family: %s;
          font-size: 6px;
          line-height: 1;
        }
      </style>
      <p>Pp</p>
    ''' % SANS_FONTS)


def test_font_variant_caps_petite(assert_pixels):
    assert_pixels('''
        ________
        _BB_BB__
        _BB_B_B_
        _B__BB__
        _B__B___
        ________
    ''', '''
      <style>
        @page {size: 8px 6px}
        p {
          color: blue;
          font-variant-caps: petite-caps;
          font-family: %s;
          font-size: 6px;
          line-height: 1;
        }
      </style>
      <p>Pp</p>
    ''' % SANS_FONTS)


# Bug in Pango: https://gitlab.gnome.org/GNOME/pango/-/merge_requests/875
@pytest.mark.xfail
def test_font_variant_caps_all_petite(assert_pixels):
    assert_pixels('''
        ________
        BB_BB___
        B_BB_B__
        BB_BB___
        B__B____
        ________
    ''', '''
      <style>
        @page {size: 8px 6px}
        p {
          color: blue;
          font-variant-caps: all-petite-caps;
          font-family: %s;
          font-size: 6px;
          line-height: 1;
        }
      </style>
      <p>Pp</p>
    ''' % SANS_FONTS)


def test_font_variant_caps_unicase(assert_pixels):
    assert_pixels('''
        ________
        BB______
        B_B_BB__
        BB__B_B_
        B___BB__
        ____B___
    ''', '''
      <style>
        @page {size: 8px 6px}
        p {
          color: blue;
          font-variant-caps: unicase;
          font-family: %s;
          font-size: 6px;
          line-height: 1;
        }
      </style>
      <p>Pp</p>
    ''' % SANS_FONTS)


def test_font_variant_caps_titling(assert_pixels):
    assert_pixels('''
        _BB_____
        _BB_____
        _BB__BB_
        _B___B_B
        _____BB_
        _____B__
    ''', '''
      <style>
        @page {size: 8px 6px}
        p {
          color: blue;
          font-family: %s;
          font-size: 6px;
          line-height: 1;
        }
      </style>
      <p>Pp</p>
    ''' % SANS_FONTS)


def test_unicode_range(assert_pixels):
    assert_pixels('''
        __________
        _RRRRRR___
        _RRRRRRzz_
        __________
    ''', '''
      <style>
        @font-face {
          font-family: uni;
          src: url(weasyprint.otf);
          unicode-range: u+41, u+043-045, u+005?;
        }
        @page {
          size: 10px 4px;
        }
        body {
          color: red;
          font-family: uni;
          font-size: 2px;
          line-height: 0;
          margin: 2px 1px;
        }
      </style>ADZB''')
