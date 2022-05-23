"""Test how leaders are drawn."""

import pytest

from ..testing_utils import assert_no_logs
from . import assert_pixels


@assert_no_logs
def test_leader_simple():
    expected_pixels = '''
        RR__BBBBBBBB__BB
        RR__BBBBBBBB__BB
        RRRR__BBBB__BBBB
        RRRR__BBBB__BBBB
        RR__BBBB__BBBBBB
        RR__BBBB__BBBBBB
    '''
    html = '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 16px 6px;
        }
        body {
          color: red;
          counter-reset: count;
          font-family: weasyprint;
          font-size: 2px;
          line-height: 1;
        }
        div::after {
          color: blue;
          content: ' ' leader(dotted) ' ' counter(count, lower-roman);
          counter-increment: count;
        }
      </style>
      <div>a</div>
      <div>bb</div>
      <div>c</div>
    '''
    assert_pixels('leader-simple', expected_pixels, html)


@assert_no_logs
def test_leader_too_long():
    expected_pixels = '''
        RRRRRRRRRR______
        RRRRRRRRRR______
        BBBBBBBBBBBB__BB
        BBBBBBBBBBBB__BB
        RR__RR__RR__RR__
        RR__RR__RR__RR__
        RR__RR__RR______
        RR__RR__RR______
        BBBBBBBBBB__BBBB
        BBBBBBBBBB__BBBB
        RR__RR__RR__RR__
        RR__RR__RR__RR__
        RR__BBBB__BBBBBB
        RR__BBBB__BBBBBB
    '''
    html = '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 16px 14px;
        }
        body {
          color: red;
          counter-reset: count;
          font-family: weasyprint;
          font-size: 2px;
          line-height: 1;
        }
        div::after {
          color: blue;
          content: ' ' leader(dotted) ' ' counter(count, lower-roman);
          counter-increment: count;
        }
      </style>
      <div>aaaaa</div>
      <div>a a a a a a a</div>
      <div>a a a a a</div>
    '''
    assert_pixels('leader-too-long', expected_pixels, html)


@assert_no_logs
def test_leader_alone():
    expected_pixels = '''
        RRBBBBBBBBBBBBBB
        RRBBBBBBBBBBBBBB
    '''
    html = '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 16px 2px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 2px;
          line-height: 1;
        }
        div::after {
          color: blue;
          content: leader(dotted);
        }
      </style>
      <div>a</div>
    '''
    assert_pixels('leader-alone', expected_pixels, html)


@assert_no_logs
def test_leader_content():
    expected_pixels = '''
        RR____BB______BB
        RR____BB______BB
    '''
    html = '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 16px 2px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 2px;
          line-height: 1;
        }
        div::after {
          color: blue;
          content: leader(' . ') 'a';
        }
      </style>
      <div>a</div>
    '''
    assert_pixels('leader-content', expected_pixels, html)


@pytest.mark.xfail
@assert_no_logs
def test_leader_float():
    expected_pixels = '''
        bbGRR___BB____BB
        bbGRR___BB____BB
        GGGRR___BB____BB
        ___RR___BB____BB
    '''
    html = '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 16px 4px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 2px;
          line-height: 1;
        }
        article {
          background: lime;
          color: navy;
          float: left;
          height: 3px;
          width: 3px;
        }
        div::after {
          color: blue;
          content: leader('. ') 'a';
        }
      </style>
      <div>a<article>a</article></div>
      <div>a</div>
    '''
    assert_pixels('leader-float', expected_pixels, html)


@pytest.mark.xfail
@assert_no_logs
def test_leader_float_small():
    expected_pixels = '''
        bbRRBB__BB____BB
        bbRRBB__BB____BB
        RR__BB__BB____BB
        RR__BB__BB____BB
    '''
    html = '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 16px 4px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 2px;
          line-height: 1;
        }
        article {
          background: lime;
          color: navy;
          float: left;
        }
        div::after {
          color: blue;
          content: leader('. ') 'a';
        }
      </style>
      <div>a<article>a</article></div>
      <div>a</div>
    '''
    assert_pixels('leader-float-small', expected_pixels, html)


@assert_no_logs
def test_leader_in_inline():
    expected_pixels = '''
        RR__GGBBBBBB__RR
        RR__GGBBBBBB__RR
    '''
    html = '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 16px 2px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 2px;
          line-height: 1;
        }
        span {
          color: lime;
        }
        span::after {
          color: blue;
          content: leader('-');
        }
      </style>
      <div>a <span>a</span> a</div>
    '''
    assert_pixels('leader-in-inline', expected_pixels, html)


@pytest.mark.xfail
@assert_no_logs
def test_leader_bad_alignment():
    expected_pixels = '''
        RRRRRR__________
        RRRRRR__________
        ______BB______RR
        ______BB______RR
    '''
    html = '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 16px 4px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 2px;
          line-height: 1;
        }
        div::after {
          color: blue;
          content: leader(' - ') 'a';
        }
      </style>
      <div>aaa</div>
    '''
    assert_pixels('leader-in-inline', expected_pixels, html)


@assert_no_logs
def test_leader_simple_rtl():
    expected_pixels = '''
        BB__BBBBBBBB__RR
        BB__BBBBBBBB__RR
        BBBB__BBBB__RRRR
        BBBB__BBBB__RRRR
        BBBBBB__BBBB__RR
        BBBBBB__BBBB__RR
    '''
    html = '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 16px 6px;
        }
        body {
          color: red;
          counter-reset: count;
          direction: rtl;
          font-family: weasyprint;
          font-size: 2px;
          line-height: 1;
        }
        div::after {
          color: blue;
          /* RTL Mark used in second space */
          content: ' ' leader(dotted) '‏ ' counter(count, lower-roman);
          counter-increment: count;
        }
      </style>
      <div>a</div>
      <div>bb</div>
      <div>c</div>
    '''
    assert_pixels('leader-simple-rtl', expected_pixels, html)


@assert_no_logs
def test_leader_too_long_rtl():
    expected_pixels = '''
        ______RRRRRRRRRR
        ______RRRRRRRRRR
        BB__BBBBBBBBBBBB
        BB__BBBBBBBBBBBB
        __RR__RR__RR__RR
        __RR__RR__RR__RR
        ______RR__RR__RR
        ______RR__RR__RR
        BBBB__BBBBBBBBBB
        BBBB__BBBBBBBBBB
        __RR__RR__RR__RR
        __RR__RR__RR__RR
        BBBBBB__BBBB__RR
        BBBBBB__BBBB__RR
    '''
    html = '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 16px 14px;
        }
        body {
          color: red;
          counter-reset: count;
          direction: rtl;
          font-family: weasyprint;
          font-size: 2px;
          line-height: 1;
        }
        div::after {
          color: blue;
          /* RTL Mark used in second space */
          content: ' ' leader(dotted) '‏ ' counter(count, lower-roman);
          counter-increment: count;
        }
      </style>
      <div>aaaaa</div>
      <div>a a a a a a a</div>
      <div>a a a a a</div>
    '''
    assert_pixels('leader-too-long-rtl', expected_pixels, html)


@assert_no_logs
def test_leader_float_leader():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/1409
    # Leaders in floats are not displayed at all in many cases with the current
    # implementation, and this case is not really specified. So…
    expected_pixels = '''
        RR____________BB
        RR____________BB
        RRRR__________BB
        RRRR__________BB
        RR____________BB
        RR____________BB
    '''
    html = '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 16px 6px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 2px;
          line-height: 1;
        }
        div::after {
          color: blue;
          content: leader(' . ') 'a';
          float: right;
        }
      </style>
      <div>a</div>
      <div>bb</div>
      <div>c</div>
    '''
    assert_pixels('leader-float-leader', expected_pixels, html)


@assert_no_logs
def test_leader_empty_string():
    expected_pixels = '''
        RRRR____
        ________
    '''
    html = '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 8px 2px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 1px;
          line-height: 1;
        }
        div::after {
          color: blue;
          content: leader('');
        }
      </style>
      <div>aaaa</div>
    '''
    assert_pixels('leader-empty-string', expected_pixels, html)


@assert_no_logs
def test_leader_zero_width_string():
    expected_pixels = '''
        RRRR____
        ________
    '''
    html = '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 8px 2px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 1px;
          line-height: 1;
        }
        div::after {
          color: blue;
          content: leader('​');  /* zero-width space */
        }
      </style>
      <div>aaaa</div>
    '''
    assert_pixels('leader-zero-width-string', expected_pixels, html)


@assert_no_logs
def test_leader_absolute():
    expected_pixels = '''
        BBBBRRRR
        ______GG
    '''
    html = '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
          size: 8px 2px;
        }
        body {
          color: red;
          font-family: weasyprint;
          font-size: 1px;
          line-height: 1;
        }
        div::before {
          color: blue;
          content: leader('z');
        }
        article {
          bottom: 0;
          color: lime;
          position: absolute;
          right: 0;
        }
      </style>
      <div>aa<article>bb</article>aa</div>
    '''
    assert_pixels('leader-absolute', expected_pixels, html)
