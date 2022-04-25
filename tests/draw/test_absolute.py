"""Test how absolutes are drawn."""

import pytest

from ..testing_utils import assert_no_logs
from . import assert_pixels


@assert_no_logs
def test_absolute_split_1():
    expected_pixels = '''
        BBBBRRRRRRRR____
        BBBBRRRRRRRR____
        BBBBRR__________
        BBBBRR__________
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
                left: 0;
                position: absolute;
                top: 0;
                width: 4px;
            }
        </style>
        <div class="split">aa aa</div>
        <div>bbbbbb bbb</div>
    '''
    assert_pixels('absolute_split_1', 16, 4, expected_pixels, html)


@assert_no_logs
def test_absolute_split_2():
    expected_pixels = '''
        RRRRRRRRRRRRBBBB
        RRRRRRRRRRRRBBBB
        RRRR________BBBB
        RRRR________BBBB
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
        <div>bbbbbb bb</div>
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


@assert_no_logs
def test_absolute_split_5():
    expected_pixels = '''
        BBBBRRRR____gggg
        BBBBRRRR____gggg
        BBBBRRRRRR__gggg
        BBBBRRRRRR__gggg
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
        <div>bbbb bbbbb</div>
    '''
    assert_pixels('absolute_split_5', 16, 4, expected_pixels, html)


@assert_no_logs
def test_absolute_split_6():
    expected_pixels = '''
        BBBBRRRR____gggg
        BBBBRRRR____gggg
        BBBBRRRRRR______
        BBBBRRRRRR______
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
        <div>bbbb bbbbb</div>
    '''
    assert_pixels('absolute_split_6', 16, 4, expected_pixels, html)


@assert_no_logs
def test_absolute_split_7():
    expected_pixels = '''
        BBBBRRRRRRRRgggg
        BBBBRRRRRRRRgggg
        ____RRRR____gggg
        ____RRRR____gggg
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
        <div class="push">bbbb bb</div>
    '''
    assert_pixels('absolute_split_7', 16, 4, expected_pixels, html)


@assert_no_logs
def test_absolute_split_8():
    expected_pixels = '''
        ______
        ______
        ______
        ______
        __RR__
        __RR__
        ______
        ______
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                margin: 2px 0;
                size: 6px 8px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div {
                position: absolute;
                left: 2px;
                top: 2px;
                width: 2px;
            }
        </style>
        <div>a a a a</div>
    '''
    assert_pixels('absolute_split_8', 6, 8, expected_pixels, html)


@assert_no_logs
def test_absolute_split_9():
    expected_pixels = '''
        ______
        ______
        BBRRBB
        BBRRBB
        BBRR__
        BBRR__
        ______
        ______
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                margin: 2px 0;
                size: 6px 8px;
            }
            body {
                color: blue;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div {
                color: red;
                position: absolute;
                left: 2px;
                top: 0;
                width: 2px;
            }
        </style>
        aaa a<div>a a a a</div>
    '''
    assert_pixels('absolute_split_9', 6, 8, expected_pixels, html)


@assert_no_logs
def test_absolute_split_10():
    expected_pixels = '''
        BB____
        BB____
        __RR__
        __RR__
        __RR__
        __RR__

        BBRR__
        BBRR__
        __RR__
        __RR__
        ______
        ______
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 6px;
            }
            body {
                color: blue;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div {
                color: red;
                position: absolute;
                left: 2px;
                top: 2px;
                width: 2px;
            }
            div + article {
                break-before: page;
            }
        </style>
        <article>a</article>
        <div>a a a a</div>
        <article>a</article>
    '''
    assert_pixels('absolute_split_10', 6, 12, expected_pixels, html)


@pytest.mark.xfail
@assert_no_logs
def test_absolute_next_page():
    # TODO: currently, the layout of absolute boxes forces to render a box,
    # even when it doesn’t fit in the page. This workaround avoids placeholders
    # with no box. Instead, we should remove these placeholders, or avoid
    # crashes when they’re rendered.
    expected_pixels = '''
        RRRRRRRRRR______
        RRRRRRRRRR______
        RRRRRRRRRR______
        RRRRRRRRRR______
        BBBBBBRRRR______
        BBBBBBRRRR______
        BBBBBB__________
        ________________
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 4px;
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
                font-size: 3px;
            }
        </style>
        aaaaa aaaaa
        <div class="split">bb</div>
        aaaaa
    '''
    assert_pixels('absolute_next_page', 16, 8, expected_pixels, html)


@assert_no_logs
def test_absolute_rtl_1():
    expected_pixels = '''
        __________RRRRRR
        __________RRRRRR
        ________________
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 3px;
            }
            div {
                color: red;
                direction: rtl;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                position: absolute;
            }
        </style>
        <div>bbb</div>
    '''
    assert_pixels('absolute_rtl_1', 16, 3, expected_pixels, html)


@assert_no_logs
def test_absolute_rtl_2():
    expected_pixels = '''
        ________________
        _________RRRRRR_
        _________RRRRRR_
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 3px;
            }
            div {
                color: red;
                direction: rtl;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                padding: 1px;
                position: absolute;
            }
        </style>
        <div>bbb</div>
    '''
    assert_pixels('absolute_rtl_2', 16, 3, expected_pixels, html)


@assert_no_logs
def test_absolute_rtl_3():
    expected_pixels = '''
        ________________
        RRRRRR__________
        RRRRRR__________
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 3px;
            }
            div {
                bottom: 0;
                color: red;
                direction: rtl;
                font-family: weasyprint;
                font-size: 2px;
                left: 0;
                line-height: 1;
                position: absolute;
            }
        </style>
        <div>bbb</div>
    '''
    assert_pixels('absolute_rtl_3', 16, 3, expected_pixels, html)


@assert_no_logs
def test_absolute_rtl_4():
    expected_pixels = '''
        ________________
        _________RRRRRR_
        _________RRRRRR_
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 3px;
            }
            div {
                color: red;
                direction: rtl;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                position: absolute;
                right: 1px;
                top: 1px;
            }
        </style>
        <div>bbb</div>
    '''
    assert_pixels('absolute_rtl_4', 16, 3, expected_pixels, html)


@assert_no_logs
def test_absolute_pages_counter():
    expected_pixels = '''
        ______
        _RR___
        _RR___
        _RR___
        _RR___
        _____B
        ______
        _RR___
        _RR___
        _BB___
        _BB___
        _____B
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                font-family: weasyprint;
                margin: 1px;
                size: 6px 6px;
                @bottom-right-corner {
                    color: blue;
                    content: counter(pages);
                    font-size: 1px;
                }
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div {
                color: blue;
                position: absolute;
            }
        </style>
        a a a <div>a a</div>
    '''
    assert_pixels('absolute_pages_counter', 6, 12, expected_pixels, html)


@assert_no_logs
def test_absolute_pages_counter_orphans():
    expected_pixels = '''
        ______
        _RR___
        _RR___
        _RR___
        _RR___
        ______
        ______
        ______
        _____B
        ______
        _RR___
        _RR___
        _BB___
        _BB___
        _GG___
        _GG___
        ______
        _____B
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                font-family: weasyprint;
                margin: 1px;
                size: 6px 9px;
                @bottom-right-corner {
                    color: blue;
                    content: counter(pages);
                    font-size: 1px;
                }
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 2;
                widows: 2;
            }
            div {
                color: blue;
                position: absolute;
            }
            div ~ div {
                color: lime;
            }
        </style>
        a a a <div>a a a</div> a <div>a a a</div>
    '''
    assert_pixels(
        'absolute_pages_counter_orphans', 6, 18, expected_pixels, html)
