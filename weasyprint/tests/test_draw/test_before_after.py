"""
    weasyprint.tests.test_draw.test_before_after
    --------------------------------------------

    Test how before and after pseudo elements are drawn.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from ..testing_utils import assert_no_logs
from . import assert_same_rendering


@assert_no_logs
def test_before_after_1():
    assert_same_rendering(300, 30, [
        ('pseudo_before', '''
            <style>
                @page { size: 300px 30px }
                body { margin: 0; background: #fff }
                a[href]:before { content: '[' attr(href) '] ' }
            </style>
            <p><a href="some url">some content</a></p>
        '''),
        ('pseudo_before_reference', '''
            <style>
                @page { size: 300px 30px }
                body { margin: 0; background: #fff }
            </style>
            <p><a href="another url"><span>[some url] </span>some content</p>
        ''')
    ], tolerance=10)


@assert_no_logs
def test_before_after_2():
    assert_same_rendering(500, 30, [
        ('pseudo_quotes', '''
            <style>
                @page { size: 500px 30px }
                body { margin: 0; background: #fff; quotes: '«' '»' '“' '”' }
                q:before { content: open-quote ' '}
                q:after { content: ' ' close-quote }
            </style>
            <p><q>Lorem ipsum <q>dolor</q> sit amet</q></p>
        '''),
        ('pseudo_quotes_reference', '''
            <style>
                @page { size: 500px 30px }
                body { margin: 0; background: #fff }
                q:before, q:after { content: none }
            </style>
            <p><span><span>« </span>Lorem ipsum
                <span><span>“ </span>dolor<span> ”</span></span>
                sit amet<span> »</span></span></p>
        ''')
    ], tolerance=10)


@assert_no_logs
def test_before_after_3():
    assert_same_rendering(100, 30, [
        ('pseudo_url', '''
            <style>
                @page { size: 100px 30px }
                body { margin: 0; background: #fff; }
                p:before { content: 'a' url(pattern.png) 'b'}
            </style>
            <p>c</p>
        '''),
        ('pseudo_url_reference', '''
            <style>
                @page { size: 100px 30px }
                body { margin: 0; background: #fff }
            </style>
            <p><span>a<img src="pattern.png" alt="Missing image">b</span>c</p>
        ''')
    ], tolerance=10)
