"""Test how footnotes in columns are drawn."""

import pytest

from ..testing_utils import assert_no_logs


@assert_no_logs
def test_footnote_column_margin_top(assert_pixels):
    assert_pixels('''
        RRRR_RRRR
        RRRR_RRRR
        _________
        _________
        _________
        RRRRRRRR_
        RRRRRRRR_
        RRRR_RRRR
        RRRR_RRRR
        RRRR_RRRR
        RRRR_RRRR
        RRRR_____
        RRRR_____
        _________
    ''', '''
    <style>
      @font-face {src: url(weasyprint.otf); font-family: weasyprint}
      @page {
        size: 9px 7px;
        @footnote {
          margin-top: 2px;
        }
      }
      div {
        color: red;
        columns: 2;
        column-gap: 1px;
        font-family: weasyprint;
        font-size: 2px;
        line-height: 1;
      }
      span {
        float: footnote;
      }
    </style>
    <div>a<span>de</span> ab ab ab ab ab ab</div>''')


@assert_no_logs
def test_footnote_column_fill_auto(assert_pixels):
    assert_pixels('''
        RRRR_____
        RRRR_____
        RRRR_____
        RRRR_____
        RRRR_____
        RRRR_____
        _________
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
    ''', '''
    <style>
      @font-face {src: url(weasyprint.otf); font-family: weasyprint}
      @page {
        size: 9px 13px;
      }
      div {
        color: red;
        columns: 2;
        column-fill: auto;
        column-gap: 1px;
        font-family: weasyprint;
        font-size: 2px;
        line-height: 1;
      }
      span {
        float: footnote;
      }
    </style>
    <div>a<span>de</span> a<span>de</span> a<span>de</span></div>''')


@assert_no_logs
def test_footnote_column_fill_auto_break_inside_avoid(assert_pixels):
    assert_pixels('''
        RRRR_RRRR
        RRRR_RRRR
        RRRR_RRRR
        RRRR_RRRR
        RRRR_RRRR
        RRRR_RRRR
        _________
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
    ''', '''
    <style>
      @font-face {src: url(weasyprint.otf); font-family: weasyprint}
      @page {
        size: 9px 13px;
      }
      div {
        color: red;
        columns: 2;
        column-fill: auto;
        column-gap: 1px;
        font-family: weasyprint;
        font-size: 2px;
        line-height: 1;
      }
      article {
        break-inside: avoid;
      }
      span {
        float: footnote;
      }
    </style>
    <div>
      <article>a<span>de</span> a<span>de</span></article>
      <article>ab</article>
      <article>a<span>de</span> ab</article>
      <article>ab</article>
    </div>''')


@assert_no_logs
def test_footnote_column_p_after(assert_pixels):
    assert_pixels('''
        RRRR_RRRR
        RRRR_RRRR
        RRRR_RRRR
        RRRR_RRRR
        KK__KK___
        KK__KK___
        _________
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        KK__KK___
        KK__KK___
        _________
        _________
        _________
        _________
        _________
        _________
        _________
        _________
        _________
    ''', '''
    <style>
      @font-face {src: url(weasyprint.otf); font-family: weasyprint}
      @page {
        size: 9px 11px;
      }
      body {
        font-family: weasyprint;
        font-size: 2px;
        line-height: 1;
      }
      div {
        color: red;
        columns: 2;
        column-gap: 1px;
      }
      span {
        float: footnote;
      }
    </style>
    <div>a<span>de</span> a<span>de</span> ab ab</div>
    <p>a a a a</p>''')


@assert_no_logs
def test_footnote_column_p_before(assert_pixels):
    assert_pixels('''
        KKKK_____
        KKKK_____
        RRRR_RRRR
        RRRR_RRRR
        RRRR_RR__
        RRRR_RR__
        _________
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        RRRR_RR__
        RRRR_RR__
        _________
        _________
        _________
        _________
        _________
        _________
        _________
        _________
        _________
        _________
        _________
    ''', '''
    <style>
      @font-face {src: url(weasyprint.otf); font-family: weasyprint}
      @page {
        size: 9px 13px;
      }
      body {
        font-family: weasyprint;
        font-size: 2px;
        line-height: 1;
      }
      div {
        color: red;
        columns: 2;
        column-gap: 1px;
      }
      span {
        float: footnote;
      }
    </style>
    <p>ab</p>
    <div>
    a<span>de</span> a<span>de</span>
    a<span>de</span> a ab a </div>''')


@assert_no_logs
def test_footnote_column_3(assert_pixels):
    assert_pixels('''
        RRRR_RRRR_RRRR
        RRRR_RRRR_RRRR
        ______________
        RRRRRRRR______
        RRRRRRRR______
        RRRR_RRRR_____
        RRRR_RRRR_____
        ______________
        ______________
        ______________
    ''', '''
    <style>
      @font-face {src: url(weasyprint.otf); font-family: weasyprint}
      @page {
        size: 14px 5px;
      }
      body {
        font-family: weasyprint;
        font-size: 2px;
        line-height: 1;
      }
      div {
        color: red;
        columns: 3;
        column-gap: 1px;
      }
      span {
        float: footnote;
      }
    </style>
    <div>ab ab a<span>de</span> ab ab </div>''')


@assert_no_logs
def test_footnote_column_3_p_before(assert_pixels):
    assert_pixels('''
        KKKK__________
        KKKK__________
        RRRR_RRRR_RRRR
        RRRR_RRRR_RRRR
        RRRR_RRRR_RRRR
        RRRR_RRRR_RRRR
        ______________
        RRRRRRRR______
        RRRRRRRR______
        RRRR_RRRR_____
        RRRR_RRRR_____
        ______________
        ______________
        ______________
        ______________
        ______________
        RRRRRRRR______
        RRRRRRRR______
    ''', '''
    <style>
      @font-face {src: url(weasyprint.otf); font-family: weasyprint}
      @page {
        size: 14px 9px;
      }
      body {
        font-family: weasyprint;
        font-size: 2px;
        line-height: 1;
      }
      div {
        color: red;
        columns: 3;
        column-gap: 1px;
      }
      span {
        float: footnote;
      }
    </style>
    <p>ab</p>
    <div>ab ab a<span>de</span> ab ab ab a<span>de</span> ab </div>''')


@assert_no_logs
def test_footnote_column_clone_decoration(assert_pixels):
    assert_pixels('''
        _________
        RRRR_RRRR
        RRRR_RRRR
        _________
        _________
        RRRRRRRR_
        RRRRRRRR_
        _________
        RRRR_RRRR
        RRRR_RRRR
        _________
        _________
        _________
        _________
    ''', '''
    <style>
      @font-face {src: url(weasyprint.otf); font-family: weasyprint}
      @page {
        size: 9px 7px;
      }
      div {
        box-decoration-break: clone;
        color: red;
        columns: 2;
        column-gap: 1px;
        font-family: weasyprint;
        font-size: 2px;
        line-height: 1;
        padding: 1px 0;
      }
      span {
        float: footnote;
      }
    </style>
    <div>a<span>de</span> ab ab ab</div>''')


@assert_no_logs
def test_footnote_column_max_height(assert_pixels):
    assert_pixels('''
        RRRR_RRRR
        RRRR_RRRR
        RRRR_RRRR
        RRRR_RRRR
        _________
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        RRRR_RRRR
        RRRR_RRRR
        _________
        _________
        _________
        _________
        _________
        RRRRRRRR_
        RRRRRRRR_
    ''', '''
    <style>
      @font-face {src: url(weasyprint.otf); font-family: weasyprint}
      @page {
        size: 9px 9px;
        @footnote {
          max-height: 2em;
        }
      }
      div {
        color: red;
        columns: 2;
        column-gap: 1px;
        font-family: weasyprint;
        font-size: 2px;
        line-height: 1;
      }
      span {
        float: footnote;
      }
    </style>
    <div>
      a<span>de</span> a<span>de</span>
      a<span>de</span> ab
      ab ab
    </div>''')


@pytest.mark.xfail
@assert_no_logs
def test_footnote_column_reported_split(assert_pixels):
    # When calling block_container_layout() in remove_placeholders(), we should
    # use the whole skip stack and not just [skip:]
    assert_pixels('''
        RRRR_RRRR
        RRRR_RRRR
        RRRR_RRRR
        RRRR_RRRR
        _________
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        RRRRRRRR_
        RRRR_____
        RRRR_____
        _________
        _________
        _________
        _________
        _________
        RRRRRRRR_
        RRRRRRRR_
    ''', '''
    <style>
      @font-face {src: url(weasyprint.otf); font-family: weasyprint}
      @page {
        size: 9px 9px;
      }
      div {
        color: red;
        columns: 2;
        column-gap: 1px;
        font-family: weasyprint;
        font-size: 2px;
        line-height: 1;
      }
      span {
        float: footnote;
      }
    </style>
    <div>
      <article>a<span>de</span> a<span>de</span></article>
      <article>a<span>de</span> ab ab</article>
    </div>''')
