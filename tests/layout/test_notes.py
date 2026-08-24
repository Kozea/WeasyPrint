"""Tests for notes layout."""

import pytest

from ..testing_utils import assert_no_logs, render_pages


@assert_no_logs
def test_one_note():
    page, = render_pages('''
        <style>
            @page {
                size: 10px 4px;
                @note-area {
                    content: element(sidenotes, all-once);
                }
            }
            div {
                font: 2px/1 weasyprint;
            }
            span {
                position: note(sidenotes);
                display: block;
            }
        </style>
        <div>abc<span>de</span></div>''')
    html, note_area = page.children
    div, = html.children[0].children
    div_textbox, note_call = div.children[0].children
    assert div_textbox.text == 'abc'
    assert note_call.children[0].text == '1'
    assert div_textbox.position_y == 2

    note_marker, note_textbox, note_callback = (
        note_area.children[0].children[0].children)
    assert note_marker.children[0].text == '1.'
    assert note_textbox.text == 'de'
    assert note_callback.children[0].text == 'b'


@assert_no_logs
def test_several_block_notes():
    page, = render_pages('''
        <style>
            @page {
                size: 30px 8px;
                @note-area {
                    content: element(sidenotes, all-once);
                }
            }
            div {
                font: 2px/1 weasyprint;
            }
            span {
                position: note(sidenotes);
                display: block;
            }
        </style>
        <div>abc<span>de</span>
          fgh<span>ij</span>
          klm<span>no</span></div>''')
    html, note_area = page.children
    div, = html.children[0].children
    div_children = div.children[0].children
    textbox1, note_call1 = div_children[0], div_children[1]
    textbox2, note_call2 = div_children[2], div_children[3]
    textbox3, note_call3 = div_children[4], div_children[5]
    assert textbox1.text == 'abc'
    assert note_call1.children[0].text == '1'
    assert textbox2.text == ' fgh'
    assert note_call2.children[0].text == '2'
    assert textbox3.text == ' klm'
    assert note_call3.children[0].text == '3'
    assert textbox1.position_y == 6
    assert textbox1.position_y == textbox2.position_y == textbox3.position_y

    note_marker1, note_textbox1, note_callback1 = (
        note_area.children[0].children[0].children)
    assert note_marker1.children[0].text == '1.'
    assert note_textbox1.text == 'de'
    assert note_callback1.children[0].text == 'b'
    note_marker2, note_textbox2, note_callback2 = (
        note_area.children[1].children[0].children)
    assert note_marker2.children[0].text == '2.'
    assert note_textbox2.text == 'ij'
    assert note_callback2.children[0].text == 'b'
    note_marker3, note_textbox3, note_callback3 = (
        note_area.children[2].children[0].children)
    assert note_marker3.children[0].text == '3.'
    assert note_textbox3.text == 'no'
    assert note_callback2.children[0].text == 'b'
