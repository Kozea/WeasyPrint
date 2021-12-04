"""
    weasyprint.tests.test_draw.test_absolute
    -------------------------------------

    Test how absolutes are drawn.

"""

import pytest

from ..testing_utils import assert_no_logs
from . import assert_pixels


@pytest.mark.xfail
@assert_no_logs
def test_absolute_split_1():
    expected_pixels = '''
        BBBBRRRRRRRR____
        BBBBRRRRRRRR____
        BBBB____________
        BBBB____________
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                position: absolute;
                top: 0;
                left: 0;
                width: 4px;
            }
        </style>
        <div class="split">aa aa</div>
        <div>bbbbbb</div>
    '''
    assert_pixels('absolute_split_1', 16, 4, expected_pixels, html)


@pytest.mark.xfail
@assert_no_logs
def test_absolute_split_2():
    expected_pixels = '''
        RRRRRRRRRRRRBBBB
        RRRRRRRRRRRRBBBB
        ____________BBBB
        ____________BBBB
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                position: absolute;
                top: 0;
                right: 0;
                width: 4px;
            }
        </style>
        <div class="split">aa aa</div>
        <div>bbbbbb</div>
    '''
    assert_pixels('absolute_split_2', 16, 4, expected_pixels, html)


@assert_no_logs
def test_absolute_split_3():
    expected_pixels = '''
        BBBBRRRRRRRR____
        BBBBRRRRRRRR____
        RRRRRRRRRR______
        RRRRRRRRRR______
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                position: absolute;
                top: 0;
                left: 0;
                width: 4px;
            }
        </style>
        <div class="split">aa</div>
        <div>bbbbbb bbbbb</div>
    '''
    assert_pixels('absolute_split_3', 16, 4, expected_pixels, html)


@assert_no_logs
def test_absolute_split_4():
    expected_pixels = '''
        RRRRRRRRRRRRBBBB
        RRRRRRRRRRRRBBBB
        RRRRRRRRRR______
        RRRRRRRRRR______
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                position: absolute;
                top: 0;
                right: 0;
                width: 4px;
            }
        </style>
        <div class="split">aa</div>
        <div>bbbbbb bbbbb</div>
    '''
    assert_pixels('absolute_split_4', 16, 4, expected_pixels, html)


@pytest.mark.xfail
@assert_no_logs
def test_absolute_split_5():
    expected_pixels = '''
        BBBBRRRR____gggg
        BBBBRRRR____gggg
        BBBB________gggg
        BBBB________gggg
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                position: absolute;
                top: 0;
                left: 0;
                width: 4px;
            }
            div.split2 {
                color: green;
                position: absolute;
                top: 0;
                right: 0;
                width: 4px;
        </style>
        <div class="split">aa aa</div>
        <div class="split2">cc cc</div>
        <div>bbbb</div>
    '''
    assert_pixels('absolute_split_5', 16, 4, expected_pixels, html)


@pytest.mark.xfail
@assert_no_logs
def test_absolute_split_6():
    expected_pixels = '''
        BBBBRRRR____gggg
        BBBBRRRR____gggg
        BBBB____________
        BBBB____________
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                position: absolute;
                width: 4px;
            }
            div.split2 {
                color: green;
                position: absolute;
                top: 0;
                right: 0;
                width: 4px;
        </style>
        <div class="split">aa aa</div>
        <div class="split2">cc</div>
        <div>bbbb</div>
    '''
    assert_pixels('absolute_split_6', 16, 4, expected_pixels, html)


@pytest.mark.xfail
@assert_no_logs
def test_absolute_split_7():
    expected_pixels = '''
        BBBBRRRRRRRRgggg
        BBBBRRRRRRRRgggg
        ____________gggg
        ____________gggg
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                position: absolute;
                width: 4px;
            }
            div.split2 {
                color: green;
                position: absolute;
                top: 0;
                right: 0;
                width: 4px;
            }
            div.push {
                margin-left: 4px;
            }
        </style>
        <div class="split">aa</div>
        <div class="split2">cc cc</div>
        <div class="push">bbbb</div>
    '''
    assert_pixels('absolute_split_7', 16, 4, expected_pixels, html)


@pytest.mark.xfail
@assert_no_logs
def test_absolute_split_8():
    expected_pixels = '''
        BBBB________gggg
        BBBB________gggg
        BBBB________gggg
        BBBB________gggg
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                position: absolute;
                width: 4px;
            }
            div.split2 {
                color: green;
                position: absolute;
                top: 0;
                right: 0;
                width: 4px;
        </style>
        <div class="split">aa aa</div>
        <div class="split2">cc cc</div>
    '''
    assert_pixels('absolute_split_8', 16, 4, expected_pixels, html)
