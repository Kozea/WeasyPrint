"""Test how footnotes are drawn."""

from ..testing_utils import assert_no_logs


@assert_no_logs
def test_inline_footnote(assert_pixels):
    assert_pixels('''
        RRRRRRRR_
        RRRRRRRR_
        _________
        _________
        _________
        RRRRRRRR_
        RRRRRRRR_
    ''', '''
    <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
            size: 9px 7px;
        }
        div {
            color: red;
            font-family: weasyprint;
            font-size: 2px;
            line-height: 1;
        }
        span {
            float: footnote;
        }
    </style>
    <div>abc<span>de</span></div>''')


@assert_no_logs
def test_block_footnote(assert_pixels):
    assert_pixels('''
        RRRRRRRR_
        RRRRRRRR_
        _________
        _________
        _________
        RRRRRRRR_
        RRRRRRRR_
    ''', '''
    <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
            size: 9px 7px;
        }
        div {
            color: red;
            font-family: weasyprint;
            font-size: 2px;
            line-height: 1;
        }
        div.footnote {
            float: footnote;
        }
    </style>
    <div>abc<div class="footnote">de</div></div>''')


@assert_no_logs
def test_long_footnote(assert_pixels):
    assert_pixels('''
        RRRRRRRR_
        RRRRRRRR_
        _________
        RRRRRRRR_
        RRRRRRRR_
        RR_______
        RR_______
    ''', '''
    <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
            size: 9px 7px;
        }
        div {
            color: red;
            font-family: weasyprint;
            font-size: 2px;
            line-height: 1;
        }
        span {
            float: footnote;
        }
    </style>
    <div>abc<span>de f</span></div>''')


@assert_no_logs
def test_footnote_margin(assert_pixels):
    assert_pixels('''
        RRRRRRRR_
        RRRRRRRR_
        _________
        _________
        _RRRRRR__
        _RRRRRR__
        _________
    ''', '''
    <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
            size: 9px 7px;

            @footnote {
                margin: 1px;
            }
        }
        div {
            color: red;
            font-family: weasyprint;
            font-size: 2px;
            line-height: 1;
        }
        span {
            float: footnote;
        }
    </style>
    <div>abc<span>d</span></div>''')


@assert_no_logs
def test_footnote_with_absolute(assert_pixels):
    assert_pixels('''
        _RRRR____
        _RRRR____
        _________
        _RRRR____
        _RRRR____
        BB_______
        BB_______
    ''', '''
    <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {
            size: 9px 7px;
            margin: 0 1px 2px;
        }
        div {
            color: red;
            font-family: weasyprint;
            font-size: 2px;
            line-height: 1;
        }
        span {
            float: footnote;
        }
        mark {
            display: block;
            position: absolute;
            left: -1px;
            color: blue;
        }
    </style>
    <div>a<span><mark>d</mark></span></div>''')
