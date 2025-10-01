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
        @page {
            size: 9Px 7px;
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
        @page {
            size: 9px 7px;
        }
        div {
            color: red;
            font-family: weasyprint;
            font-size: 2PX;
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
def test_footnote_multiple_margin(assert_pixels):
    assert_pixels('''
        RRRR___
        RRRR___
        RRRR___
        RRRR___
        RRRR___
        RRRR___
        RRRRRR_
        RRRRRR_
        _______
        _______

        RRRR___
        RRRR___
        _______
        _______
        _______
        _______
        RRRRRR_
        RRRRRR_
        RRRRRR_
        RRRRRR_
    ''', '''
    <style>
        @page {
            size: 7px 10Px;

            @footnote {
                margin-top: 1px;
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
    <div>ab</div>
    <div>ab</div>
    <div>ab</div>
    <div>a<span>d</span><span>e</span></div>
    <div>ab</div>''')


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


@assert_no_logs
def test_footnote_max_height_1(assert_pixels):
    assert_pixels('''
        RRRRKKKK_
        RRRRKKKK_
        RRRR_____
        RRRR_____
        _GGGGBB__
        _GGGGBB__
        _________
        _________
        _________
        _________
        _GGGGBB__
        _GGGGBB__
    ''', '''
    <style>
        @page {
            size: 9px 6px;

            @footnote {
                margin-left: 1px;
                max-height: 3px;
            }
        }
        div {
            color: red;
            font-family: weasyprint;
            font-size: 2px;
            line-height: 1;
        }
        div.footnote {
            float: footnote;
            color: blue;
            &::footnote-call { color: black }
            &::footnote-marker { color: lime }
        }
    </style>
    <div>ab<div class="footnote">c</div><div class="footnote">d</div></div>
    <div>ef</div>''')


@assert_no_logs
def test_footnote_max_height_2(assert_pixels):
    assert_pixels('''
        RRRRRRRR_
        RRRRRRRR_
        _________
        _________
        _BBBBBB__
        _BBBBBB__
        _________
        _________
        _________
        _________
        _BBBBBB__
        _BBBBBB__
    ''', '''
    <style>
        @page {
            size: 9px 6px;

            @footnote {
                margin-left: 1px;
                max-height: 3px;
            }
        }
        div {
            color: red;
            font-family: weasyprint;
            font-size: 2px;
            line-height: 1;
        }
        div.footnote {
            float: footnote;
            color: blue;
            &::footnote-call { color: red }
        }
    </style>
    <div>ab<div class="footnote">c</div><div class="footnote">d</div></div>''')


@assert_no_logs
def test_footnote_max_height_3(assert_pixels):
    # This case is crazy and the rendering is not really defined, but this test
    # is useful to check that there’s no endless loop.
    assert_pixels('''
        RRRRRRRR_
        RRRRRRRR_
        _________
        _________
        _________
        _________
        _________
        _________
        _________
        _________
        _________
        _BBBBBB__
        _________
        _________
        _________
        _________
        _________
        _BBBBBB__
    ''', '''
    <style>
        @page {
            size: 9px 6px;

            @footnote {
                margin-left: 1px;
                max-height: 1px;
            }
        }
        div {
            color: red;
            font-family: weasyprint;
            font-size: 2px;
            line-height: 1;
        }
        div.footnote {
            float: footnote;
            color: blue;
            &::footnote-call { color: red }
        }
    </style>
    <div>ab<div class="footnote">c</div><div class="footnote">d</div></div>''')


@assert_no_logs
def test_footnote_max_height_4(assert_pixels):
    assert_pixels('''
        RRRRRRRR_
        RRRRRRRR_
        RRRR_____
        RRRR_____
        _BBBBBB__
        _BBBBBB__
        RRRR_____
        RRRR_____
        _________
        _________
        _BBBBBB__
        _BBBBBB__
    ''', '''
    <style>
        @page {
            size: 9px 6px;

            @footnote {
                margin-left: 1px;
                max-height: 3px;
            }
        }
        div {
            color: red;
            font-family: weasyprint;
            font-size: 2px;
            line-height: 1;
        }
        div.footnote {
            float: footnote;
            color: blue;
            &::footnote-call { color: red }
        }
    </style>
    <div>ab<div class="footnote">c</div><div class="footnote">d</div></div>
    <div>ef</div>
    <div>gh</div>''')


@assert_no_logs
def test_footnote_max_height_5(assert_pixels):
    assert_pixels('''
        RRRRRRRR__RR
        RRRRRRRR__RR
        _BBBBBB_____
        _BBBBBB_____
        _BBBBBB_____
        _BBBBBB_____
        RRRR________
        RRRR________
        ____________
        ____________
        _BBBBBB_____
        _BBBBBB_____
    ''', '''
    <style>
        @page {
            size: 12px 6px;

            @footnote {
                margin-left: 1px;
                max-height: 4px;
            }
        }
        div {
            color: red;
            font-family: weasyprint;
            font-size: 2px;
            line-height: 1;
        }
        div.footnote {
            float: footnote;
            color: blue;
            &::footnote-call { color: red }
        }
    </style>
    <div>ab<div class="footnote">c</div><div class="footnote">d</div>
    <div class="footnote">e</div></div>
    <div>fg</div>''')
