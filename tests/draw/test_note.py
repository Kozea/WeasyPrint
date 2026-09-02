"""Test how notes are drawn."""

import pytest

from ..testing_utils import assert_no_logs


@assert_no_logs
def test_one_note(assert_pixels):
    assert_pixels('''
        BBBBBBBBBB
        BBBBBBBBBB
        RRRRRRRR__
        RRRRRRRR__
    ''', '''
        <style>
            @page {
                size: 10px 4px;
                @note-area {
                    content: element(sidenotes, all-once);
                }
            }
            div {
                color: red;
                font: 2px/1 weasyprint;
            }
            span {
                color: blue;
                display: block;
                position: note(sidenotes);

                &::note-call { color: red}
            }
        </style>
        <div>abc<span>de</span></div>''')


@assert_no_logs
def test_several_note(assert_pixels):
    assert_pixels('''
        BBBBBBBBBB______
        BBBBBBBBBB______
        BBBBBBBBBB______
        BBBBBBBBBB______
        RRRRRRRRRRRRRRRR
        RRRRRRRRRRRRRRRR
    ''', '''
        <style>
            @page {
                size: 16px 6px;
                @note-area {
                    content: element(sidenotes, all-once);
                }
            }
            div {
                color: red;
                font: 2px/1 weasyprint;
            }
            span {
                color: blue;
                display: block;
                position: note(sidenotes);

                &::note-call { color: red}
            }
        </style>
        <div>abc<span>de</span>fgh<span>ij</span></div>''')


@assert_no_logs
def test_inline_note(assert_pixels):
    assert_pixels('''
        BBBBBBBBBBBBBBBBBBBB
        BBBBBBBBBBBBBBBBBBBB
        RRRRRRRRRRRRRRRR____
        RRRRRRRRRRRRRRRR____
    ''', '''
        <style>
            @page {
                size: 20px 4px;
                @note-area {
                    content: element(sidenotes, all-once);
                    font: 2px/1 weasyprint;
                }
            }
            div {
                color: red;
                font: 2px/1 weasyprint;
            }
            span {
                color: blue;
                display: inline;
                position: note(sidenotes);

                &::note-call { color: red }
            }
        </style>
        <div>abc<span>de</span>fgh<span>ij</span></div>''')


@assert_no_logs
def test_absolute_note(assert_pixels):
    assert_pixels('''
        RRRRRRRRRRRRRRRR
        RRRRRRRRRRRRRRRR
        ________________
        ________________
        ______RRRRRRRRRR
        ______RRRRRRRRRR
        ______RRRRRRRRRR
        ______RRRRRRRRRR
    ''', '''
        <style>
            @page {
                size: 16px 8px;
                @note-area {
                    content: element(sidenotes, all-once);
                    position: absolute;
                    bottom: 0;
                    right: 0;
                    width: calc(10 / 16 * 100%);
                }
            }
            div {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            span {
                display: block;
                position: note(sidenotes);
            }
        </style>
        <div>abc<span>de</span>fgh<span>ij</span></div>''')


@assert_no_logs
def test_float_left_note(assert_pixels):
    assert_pixels('''
        BBBBBBBBRRRRRRBB
        BBBBBBBBRRRRRRBB
        BBBBBBBBRRRRRRBB
        BBBBBBBBRRRRRRBB
    ''', '''
        <style>
            @page {
                size: 16px 4px;
                @note-area {
                    content: element(sidenotes, all-once);
                    float: left;
                    width: 50%;
                }
            }
            div {
                color: red;
                font: 2px/1 weasyprint;
            }
            span {
                color: blue;
                display: block;
                position: note(sidenotes);
            }
        </style>
        <div>abc<span>d</span>
          fgh<span>i</span></div>''')


@assert_no_logs
def test_float_right_note(assert_pixels):
    assert_pixels('''
        RRRRRRBBBBBBBBBB
        RRRRRRBBBBBBBBBB
        RRRRRRBBBBBBBBBB
        RRRRRRBBBBBBBBBB
    ''', '''
        <style>
            @page {
                size: 16px 4px;
                @note-area {
                    content: element(sidenotes, all-once);
                    float: right;
                    width: 50%;
                }
            }
            div {
                color: red;
                font: 2px/1 weasyprint;
            }
            span {
                color: blue;
                display: block;
                position: note(sidenotes);
            }
        </style>
        <div>abc<span>d</span>
          fgh<span>i</span></div>''')


@assert_no_logs
def test_float_left_margin_note(assert_pixels):
    assert_pixels('''
        ________________________
        ________________________
        __BBBBBBBB______________
        __BBBBBBBB______________
        __BBBBBBBB__RRRRRRBB____
        __BBBBBBBB__RRRRRRBB____
        ____________RRRRRRBB____
        ____________RRRRRRBB____
        ____RRRRRRRRRR__________
        ____RRRRRRRRRR__________
        ________________________
        ________________________
        ________________________
        ________________________
    ''', '''
        <style>
            @page {
                size: 24px 14px;
                margin: 4px;
                @note-area {
                    content: element(sidenotes, all-once);
                    float: left;
                    margin: -2px 2px 2px -2px;
                    width: 50%;
                }
            }
            div {
                color: red;
                font: 2px/1 weasyprint;
            }
            span {
                color: blue;
                display: block;
                position: note(sidenotes);
            }
        </style>
        <div>abc<span>d</span>
          fgh<span>i</span>
          jklmn</div>''')


@assert_no_logs
def test_flex_note(assert_pixels):
    assert_pixels('''
        BBBBBBBBBBBBBBBB
        BBBBBBBBBBBBBBBB
        RRRRRRBBRRRRRRBB
        RRRRRRBBRRRRRRBB
    ''', '''
        <style>
            @page {
                size: 16px 4px;
                @note-area {
                    content: element(sidenotes, all-once);
                    display: flex;
                    flex-wrap: wrap;
                }
            }
            div {
                color: red;
                font: 2px/1 weasyprint;
            }
            span {
                color: blue;
                display: block;
                position: note(sidenotes);
            }
        </style>
        <div>abc<span>d</span>fgh<span>i</span></div>''')


@assert_no_logs
def test_grid_note(assert_pixels):
    assert_pixels('''
        BBBBBBBB__BBBBBBBB
        BBBBBBBB__BBBBBBBB
        RRRRRRBBRRRRRRBB__
        RRRRRRBBRRRRRRBB__
    ''', '''
        <style>
            @page {
                size: 18px 4px;
                @note-area {
                    content: element(sidenotes, all-once);
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 2px;
                }
            }
            div {
                color: red;
                font: 2px/1 weasyprint;
            }
            span {
                color: blue;
                display: block;
                position: note(sidenotes);
            }
        </style>
        <div>abc<span>d</span>fgh<span>i</span></div>''')


@assert_no_logs
def test_next_page_note(assert_pixels):
    assert_pixels('''
        BBBBBBBB________
        BBBBBBBB________
        BBBBBBBB________
        BBBBBBBB________
        RRRRRRRRRRRRRRRR
        RRRRRRRRRRRRRRRR
        RRRRRRBBRRRRRRBB
        RRRRRRBBRRRRRRBB
        ________________
        ________________
        ________________
        ________________
    ''', '''
        <style>
            @page {
                size: 16px 6px;
                @note-area {
                    content: element(sidenotes, all-once);
                }
            }
            div {
                color: red;
                font: 2px/1 weasyprint;
            }
            span {
                color: blue;
                display: block;
                position: note(sidenotes);
            }
        </style>
        <div>aaaaaaaa
          abc<span>d</span>fgh<span>i</span></div>''')


@assert_no_logs
def test_next_page_split_note(assert_pixels):
    assert_pixels('''
        BBBBBBBB________
        BBBBBBBB________
        RRRRRRBB________
        RRRRRRBB________
        RRRRRRRRRRRRRRRR
        RRRRRRRRRRRRRRRR
        BBBBBBBB________
        BBBBBBBB________
        RRRRRRRRRRRRRRRR
        RRRRRRRRRRRRRRRR
        RRRRRRBB________
        RRRRRRBB________
    ''', '''
        <style>
            @page {
                size: 16px 6px;
                @note-area {
                    content: element(sidenotes, all-once);
                }
            }
            div {
                color: red;
                font: 2px/1 weasyprint;
            }
            span {
                color: blue;
                display: block;
                position: note(sidenotes);
            }
        </style>
        <div>abc<span>d</span>
          aaaaaaaa
          aaaaaaaa
          fgh<span>i</span></div>''')


@pytest.mark.xfail
@assert_no_logs
def test_next_page_split_not_fitted_note(assert_pixels):
    assert_pixels('''
        RRRRRRRRRRRRRRRR
        RRRRRRRRRRRRRRRR
        RRRRRRRRRRRRRRRR
        RRRRRRRRRRRRRRRR
        RRRRRRBB________
        RRRRRRBB________
        BBBBBBBB________
        BBBBBBBB________
        RRRRRRRRRRRRRRRR
        RRRRRRRRRRRRRRRR
        RRRRRRBB________
        RRRRRRBB________
        BBBBBBBB________
        BBBBBBBB________
        ________________
        ________________
        ________________
        ________________
    ''', '''
        <style>
            @page {
                size: 16px 6px;
                @note-area {
                    content: element(sidenotes, all-once);
                }
            }
            div {
                color: red;
                font: 2px/1 weasyprint;
            }
            span {
                color: blue;
                display: block;
                position: note(sidenotes);
            }
        </style>
        <div>
          aaaaaaaa
          aaaaaaaa
          abc<span>d</span>
          aaaaaaaa
          fgh<span>i</span></div>''')




@pytest.mark.xfail
@assert_no_logs
def test_next_page_split_not_fitted_note_2(assert_pixels):
    assert_pixels('''
        RRRRRRRRRRRRRRRR
        RRRRRRRRRRRRRRRR
        RRRRRRRRRRRRRRRR
        RRRRRRRRRRRRRRRR
        RRRRRRBB________
        RRRRRRBB________
        BBBBBBBB________
        BBBBBBBB________
        BBBBBBBB________
        BBBBBBBB________
        RRRRRRBB________
        RRRRRRBB________
    ''', '''
        <style>
            @page {
                size: 16px 6px;
                @note-area {
                    content: element(sidenotes, all-once);
                }
            }
            div {
                color: red;
                font: 2px/1 weasyprint;
            }
            span {
                color: blue;
                display: block;
                position: note(sidenotes);
            }
        </style>
        <div>
          aaaaaaaa
          aaaaaaaa
          abc<span>d</span>
          fgh<span>i</span></div>''')


@pytest.mark.xfail
@assert_no_logs
def test_next_page_split_not_fitted_note_3(assert_pixels):
    assert_pixels('''
        BBBBBBBB________
        BBBBBBBB________
        RRRRRRBB________
        RRRRRRBB________
        RRRRRRRRRRRRRRRR
        RRRRRRRRRRRRRRRR
        BBBBBBBB________
        BBBBBBBB________
        RRRRRRBB________
        RRRRRRBB________
        ________________
        ________________
    ''', '''
        <style>
            @page {
                size: 16px 6px;
                @note-area {
                    content: element(sidenotes, all-once);
                }
            }
            div {
                color: red;
                font: 2px/1 weasyprint;
            }
            span {
                color: blue;
                display: block;
                position: note(sidenotes);
            }
        </style>
        <div>abc<span>d</span>
          aaaaaaaa
          fgh<span>i</span></div>''')
