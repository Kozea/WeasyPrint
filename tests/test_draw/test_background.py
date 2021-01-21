"""
    weasyprint.tests.test_draw.test_background
    ------------------------------------------

    Test how backgrounds are drawn.

"""

import pytest

from ..testing_utils import assert_no_logs
from . import assert_pixels


@assert_no_logs
@pytest.mark.parametrize(
    'name, expected_width, expected_height, expected_pixels, html', (
        ('all_blue', 10, 10, (10 * (10 * 'B' + '\n')), '''
           <style>
             @page { size: 10px }
             /* body’s background propagates to the whole canvas */
             body { margin: 2px; background: #00f; height: 5px }
           </style>
         <body>'''),
        ('blocks', 10, 10, '''
             rrrrrrrrrr
             rrrrrrrrrr
             rrBBBBBBrr
             rrBBBBBBrr
             rrBBBBBBrr
             rrBBBBBBrr
             rrBBBBBBrr
             rrrrrrrrrr
             rrrrrrrrrr
             rrrrrrrrrr
         ''', '''
           <style>
             @page { size: 10px }
             /* html’s background propagates to the whole canvas */
             html { padding: 1px; background: #f00 }
             /* html has a background, so body’s does not propagate */
             body { margin: 1px; background: #00f; height: 5px }
          </style>
          <body>'''),
    ))
def test_canvas_background(name, expected_width, expected_height,
                           expected_pixels, html):
    assert_pixels(name, expected_width, expected_height, expected_pixels, html)


def test_canvas_background_size():
    expected_pixels = '''
        __________
        __________
        __RRRRRR__
        __RGGGGR__
        __RRRRRR__
        __BBBBBB__
        __BBBBBB__
        __BBBBBB__
        __________
        __________
    '''
    html = '''
      <style>
         @page { size: 10px; margin: 2px; background: white }
         /* html’s background propagates to the whole canvas */
         html { background: linear-gradient(
           red 0, red 50%, blue 50%, blue 100%); }
         /* html has a background, so body’s does not propagate */
         body { margin: 1px; background: lime; height: 1px }
      </style>
      <body>'''
    assert_pixels('background-size', 10, 10, expected_pixels, html)


@assert_no_logs
@pytest.mark.parametrize('name, css, pixels', (
    ('repeat', 'url(pattern.png)', '''
        ______________
        ______________
        __rBBBrBBBrB__
        __BBBBBBBBBB__
        __BBBBBBBBBB__
        __BBBBBBBBBB__
        __rBBBrBBBrB__
        __BBBBBBBBBB__
        __BBBBBBBBBB__
        __BBBBBBBBBB__
        __rBBBrBBBrB__
        __BBBBBBBBBB__
        ______________
        ______________
        ______________
        ______________
    '''),
    ('repeat_x', 'url(pattern.png) repeat-x', '''
        ______________
        ______________
        __rBBBrBBBrB__
        __BBBBBBBBBB__
        __BBBBBBBBBB__
        __BBBBBBBBBB__
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    ('repeat_y', 'url(pattern.png) repeat-y', '''
        ______________
        ______________
        __rBBB________
        __BBBB________
        __BBBB________
        __BBBB________
        __rBBB________
        __BBBB________
        __BBBB________
        __BBBB________
        __rBBB________
        __BBBB________
        ______________
        ______________
        ______________
        ______________
    '''),

    ('left_top', 'url(pattern.png) no-repeat 0 0%', '''
        ______________
        ______________
        __rBBB________
        __BBBB________
        __BBBB________
        __BBBB________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    ('center_top', 'url(pattern.png) no-repeat 50% 0px', '''
        ______________
        ______________
        _____rBBB_____
        _____BBBB_____
        _____BBBB_____
        _____BBBB_____
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    ('right_top', 'url(pattern.png) no-repeat 6px top', '''
        ______________
        ______________
        ________rBBB__
        ________BBBB__
        ________BBBB__
        ________BBBB__
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    ('bottom_6_right_0', 'url(pattern.png) no-repeat bottom 6px right 0', '''
        ______________
        ______________
        ________rBBB__
        ________BBBB__
        ________BBBB__
        ________BBBB__
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    ('left_center', 'url(pattern.png) no-repeat left center', '''
        ______________
        ______________
        ______________
        ______________
        ______________
        __rBBB________
        __BBBB________
        __BBBB________
        __BBBB________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    ('center_left', 'url(pattern.png) no-repeat center left', '''
        ______________
        ______________
        ______________
        ______________
        ______________
        __rBBB________
        __BBBB________
        __BBBB________
        __BBBB________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    ('center_center', 'url(pattern.png) no-repeat 3px 3px', '''
        ______________
        ______________
        ______________
        ______________
        ______________
        _____rBBB_____
        _____BBBB_____
        _____BBBB_____
        _____BBBB_____
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    ('right_center', 'url(pattern.png) no-repeat 100% 50%', '''
        ______________
        ______________
        ______________
        ______________
        ______________
        ________rBBB__
        ________BBBB__
        ________BBBB__
        ________BBBB__
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),

    ('left_bottom', 'url(pattern.png) no-repeat 0% bottom', '''
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        __rBBB________
        __BBBB________
        __BBBB________
        __BBBB________
        ______________
        ______________
        ______________
        ______________
    '''),
    ('center_bottom', 'url(pattern.png) no-repeat center 6px', '''
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        _____rBBB_____
        _____BBBB_____
        _____BBBB_____
        _____BBBB_____
        ______________
        ______________
        ______________
        ______________
    '''),
    ('bottom_center', 'url(pattern.png) no-repeat bottom center', '''
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        _____rBBB_____
        _____BBBB_____
        _____BBBB_____
        _____BBBB_____
        ______________
        ______________
        ______________
        ______________
    '''),
    ('right_bottom', 'url(pattern.png) no-repeat 6px 100%', '''
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ________rBBB__
        ________BBBB__
        ________BBBB__
        ________BBBB__
        ______________
        ______________
        ______________
        ______________
    '''),

    ('repeat_x_1px_2px', 'url(pattern.png) repeat-x 1px 2px', '''
        ______________
        ______________
        ______________
        ______________
        __BrBBBrBBBr__
        __BBBBBBBBBB__
        __BBBBBBBBBB__
        __BBBBBBBBBB__
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    ('repeat_y_local_2px_1px', 'url(pattern.png) repeat-y local 2px 1px', '''
        ______________
        ______________
        ____BBBB______
        ____rBBB______
        ____BBBB______
        ____BBBB______
        ____BBBB______
        ____rBBB______
        ____BBBB______
        ____BBBB______
        ____BBBB______
        ____rBBB______
        ______________
        ______________
        ______________
        ______________
    '''),

    ('fixed', 'url(pattern.png) no-repeat fixed', '''
        # The image is actually here:
        #######
        ______________
        ______________
        __BB__________
        __BB__________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    ('fixed_right', 'url(pattern.png) no-repeat fixed right 3px', '''
        #                   x x x x
        ______________
        ______________
        ______________
        __________rB__   #
        __________BB__   #
        __________BB__   #
        __________BB__   #
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    ('fixed_center_center', 'url(pattern.png)no-repeat fixed 50%center', '''
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        _____rBBB_____
        _____BBBB_____
        _____BBBB_____
        _____BBBB_____
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    ('multi_under', '''url(pattern.png) no-repeat,
                       url(pattern.png) no-repeat 2px 1px''', '''
        ______________
        ______________
        __rBBB________
        __BBBBBB______
        __BBBBBB______
        __BBBBBB______
        ____BBBB______
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    ('multi_over', '''url(pattern.png) no-repeat 2px 1px,
                      url(pattern.png) no-repeat''', '''
        ______________
        ______________
        __rBBB________
        __BBrBBB______
        __BBBBBB______
        __BBBBBB______
        ____BBBB______
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
))
def test_background_image(name, css, pixels):
    # pattern.png looks like this:

    #    rBBB
    #    BBBB
    #    BBBB
    #    BBBB

    assert_pixels(f'background_{name}', 14, 16, pixels, '''
      <style>
        @page { size: 14px 16px }
        html { background: #fff }
        body { margin: 2px; height: 10px;
               background: %s }
        p { background: none }
      </style>
      <body>
      <p>&nbsp;''' % css)


@assert_no_logs
def test_background_image_zero_size_background():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/217
    assert_pixels('zero_size_background', 10, 10, '''
        __________
        __________
        __________
        __________
        __________
        __________
        __________
        __________
        __________
        __________
    ''', '''
      <style>
        @page { size: 10px }
        html { background: #fff }
        body { background: url(pattern.png);
               background-size: cover;
               display: inline-block }
      </style>
      <body>''')


@assert_no_logs
def test_background_origin():
    """Test the background-origin property."""
    def test_value(value, pixels, css=None):
        assert_pixels(f'background_origin_{value}', 12, 12, pixels, '''
            <style>
                @page { size: 12px }
                html { background: #fff }
                body { margin: 1px; padding: 1px; height: 6px;
                       border: 1px solid  transparent;
                       background: url(pattern.png) bottom right no-repeat;
                       background-origin: %s }
            </style>
            <body>''' % (css or value,))

    test_value('border-box', '''
        ____________
        ____________
        ____________
        ____________
        ____________
        ____________
        ____________
        _______rBBB_
        _______BBBB_
        _______BBBB_
        _______BBBB_
        ____________
    ''')
    test_value('padding-box', '''
        ____________
        ____________
        ____________
        ____________
        ____________
        ____________
        ______rBBB__
        ______BBBB__
        ______BBBB__
        ______BBBB__
        ____________
        ____________
    ''')
    test_value('content-box', '''
        ____________
        ____________
        ____________
        ____________
        ____________
        _____rBBB___
        _____BBBB___
        _____BBBB___
        _____BBBB___
        ____________
        ____________
        ____________
    ''')

    test_value('border-box_clip', '''
        ____________
        ____________
        ____________
        ____________
        ____________
        ____________
        ____________
        _______rB___
        _______BB___
        ____________
        ____________
        ____________
    ''', css='border-box; background-clip: content-box')


@assert_no_logs
def test_background_repeat_space_1():
    assert_pixels('background_repeat_space', 12, 16, '''
        ____________
        _rBBB__rBBB_
        _BBBB__BBBB_
        _BBBB__BBBB_
        _BBBB__BBBB_
        ____________
        _rBBB__rBBB_
        _BBBB__BBBB_
        _BBBB__BBBB_
        _BBBB__BBBB_
        ____________
        _rBBB__rBBB_
        _BBBB__BBBB_
        _BBBB__BBBB_
        _BBBB__BBBB_
        ____________
    ''', '''
      <style>
        @page { size: 12px 16px }
        html { background: #fff }
        body { margin: 1px; height: 14px;
               background: url(pattern.png) space; }
      </style>
      <body>''')


@assert_no_logs
def test_background_repeat_space_2():
    assert_pixels('background_repeat_space', 12, 14, '''
        ____________
        _rBBB__rBBB_
        _BBBB__BBBB_
        _BBBB__BBBB_
        _BBBB__BBBB_
        _rBBB__rBBB_
        _BBBB__BBBB_
        _BBBB__BBBB_
        _BBBB__BBBB_
        _rBBB__rBBB_
        _BBBB__BBBB_
        _BBBB__BBBB_
        _BBBB__BBBB_
        ____________
    ''', '''
      <style>
        @page { size: 12px 14px }
        html { background: #fff }
        body { margin: 1px; height: 12px;
               background: url(pattern.png) space; }
      </style>
      <body>''')


@assert_no_logs
def test_background_repeat_space_3():
    assert_pixels('background_repeat_space', 12, 13, '''
        ____________
        _rBBBrBBBrB_
        _BBBBBBBBBB_
        _BBBBBBBBBB_
        _BBBBBBBBBB_
        ____________
        ____________
        ____________
        _rBBBrBBBrB_
        _BBBBBBBBBB_
        _BBBBBBBBBB_
        _BBBBBBBBBB_
        ____________
    ''', '''
      <style>
        @page { size: 12px 13px }
        html { background: #fff }
        body { margin: 1px; height: 11px;
               background: url(pattern.png) repeat space; }
      </style>
      <body>''')


@assert_no_logs
def test_background_repeat_round_1():
    assert_pixels('background_repeat_round', 10, 14, '''
        __________
        _rrBBBBBB_
        _rrBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _rrBBBBBB_
        _rrBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        __________
    ''', '''
      <style>
        @page { size: 10px 14px }
        html { background: #fff }
        body { margin: 1px; height: 12px;
               image-rendering: pixelated;
               background: url(pattern.png) top/6px round repeat; }
      </style>
      <body>''')


@assert_no_logs
def test_background_repeat_round_2():
    assert_pixels('background_repeat_round', 10, 18, '''
        __________
        _rrBBBBBB_
        _rrBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _rrBBBBBB_
        _rrBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        __________
    ''', '''
      <style>
        @page { size: 10px 18px }
        html { background: #fff }
        body { margin: 1px; height: 16px;
               image-rendering: pixelated;
               background: url(pattern.png) center/auto 8px repeat round; }
      </style>
      <body>''')


@assert_no_logs
def test_background_repeat_round_3():
    assert_pixels('background_repeat_round', 10, 14, '''
        __________
        _rrBBBBBB_
        _rrBBBBBB_
        _rrBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        __________
    ''', '''
      <style>
        @page { size: 10px 14px }
        html { background: #fff }
        body { margin: 1px; height: 12px;
               image-rendering: pixelated;
               background: url(pattern.png) center/6px 9px round; }
      </style>
      <body>''')


@assert_no_logs
def test_background_repeat_round_4():
    assert_pixels('background_repeat_round', 10, 14, '''
        __________
        _rBBBrBBB_
        _rBBBrBBB_
        _rBBBrBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        __________
    ''', '''
      <style>
        @page { size: 10px 14px }
        html { background: #fff }
        body { margin: 1px; height: 12px;
               image-rendering: pixelated;
               background: url(pattern.png) center/5px 9px round; }
      </style>
      <body>''')


@assert_no_logs
@pytest.mark.parametrize('value, pixels', (
    ('#00f border-box', '''
        ________
        _BBBBBB_
        _BBBBBB_
        _BBBBBB_
        _BBBBBB_
        _BBBBBB_
        _BBBBBB_
        ________
    '''),
    ('#00f padding-box', '''
        ________
        ________
        __BBBB__
        __BBBB__
        __BBBB__
        __BBBB__
        ________
        ________
    '''),
    ('#00f content-box', '''
        ________
        ________
        ________
        ___BB___
        ___BB___
        ________
        ________
        ________
    '''),
    ('url(pattern.png) padding-box, #0f0', '''
        ________
        _GGGGGG_
        _GrBBBG_
        _GBBBBG_
        _GBBBBG_
        _GBBBBG_
        _GGGGGG_
        ________
    '''),
))
def test_background_clip(value, pixels):
    assert_pixels(f'background_clip_{value}', 8, 8, pixels, '''
      <style>
        @page { size: 8px }
        html { background: #fff }
        body { margin: 1px; padding: 1px; height: 2px;
               border: 1px solid  transparent;
               background: %s }
      </style>
      <body>''' % value)


@assert_no_logs
@pytest.mark.parametrize(
    'name, expected_width, expected_height, expected_pixels, html', (
        ('background_size', 12, 12, '''
             ____________
             ____________
             ____________
             ___rrBBBBBB_
             ___rrBBBBBB_
             ___BBBBBBBB_
             ___BBBBBBBB_
             ___BBBBBBBB_
             ___BBBBBBBB_
             ___BBBBBBBB_
             ___BBBBBBBB_
             ____________
         ''', '''
           <style>
             @page { size: 12px }
             html { background: #fff }
             body { margin: 1px; height: 10px;
                    /* Use nearest neighbor algorithm for image resizing: */
                    image-rendering: pixelated;
                    background: url(pattern.png) no-repeat
                                bottom right / 80% 8px; }
           </style>
           <body>'''),
        ('background_size_auto', 12, 12, '''
             ____________
             ____________
             ____________
             ____________
             ____________
             ____________
             ____________
             _______rBBB_
             _______BBBB_
             _______BBBB_
             _______BBBB_
             ____________
         ''', '''
           <style>
             @page { size: 12px }
             html { background: #fff }
             body { margin: 1px; height: 10px;
                    /* Use nearest neighbor algorithm for image resizing: */
                    image-rendering: pixelated;
                    background: url(pattern.png) bottom right/auto no-repeat }
           </style>
           <body>'''),
        ('background_size_contain', 14, 10, '''
             ______________
             _rrBBBBBB_____
             _rrBBBBBB_____
             _BBBBBBBB_____
             _BBBBBBBB_____
             _BBBBBBBB_____
             _BBBBBBBB_____
             _BBBBBBBB_____
             _BBBBBBBB_____
             ______________
         ''', '''
           <style>
             @page { size: 14px 10px }
             html { background: #fff }
             body { margin: 1px; height: 8px;
                    /* Use nearest neighbor algorithm for image resizing: */
                    image-rendering: pixelated;
                    background: url(pattern.png) no-repeat;
                    background-size: contain }
           </style>
           <body>'''),

        ('background_size_mixed', 14, 10, '''
             ______________
             _rrBBBBBB_____
             _rrBBBBBB_____
             _BBBBBBBB_____
             _BBBBBBBB_____
             _BBBBBBBB_____
             _BBBBBBBB_____
             _BBBBBBBB_____
             _BBBBBBBB_____
             ______________
         ''', '''
           <style>
             @page { size: 14px 10px }
             html { background: #fff }
             body { margin: 1px; height: 8px;
                    /* Use nearest neighbor algorithm for image resizing: */
                    image-rendering: pixelated;
                    background: url(pattern.png) no-repeat left / auto 8px;
                    clip: auto; /* no-op to cover more validation */ }
           </style>
           <body>'''),
        ('background_size_double', 14, 10, '''
             ______________
             _rrBBBBBB_____
             _BBBBBBBB_____
             _BBBBBBBB_____
             _BBBBBBBB_____
             ______________
             ______________
             ______________
             ______________
             ______________
         ''', '''
           <style>
             @page { size: 14px 10px }
             html { background: #fff }
             body { margin: 1px; height: 8px;
                    /* Use nearest neighbor algorithm for image resizing: */
                    image-rendering: pixelated;
                    background: url(pattern.png) no-repeat 0 0 / 8px 4px;
                    clip: auto; /* no-op to cover more validation */ }
           </style>
           <body>'''),
        ('background_size_cover', 14, 10, '''
             ______________
             _rrrBBBBBBBBB_
             _rrrBBBBBBBBB_
             _rrrBBBBBBBBB_
             _BBBBBBBBBBBB_
             _BBBBBBBBBBBB_
             _BBBBBBBBBBBB_
             _BBBBBBBBBBBB_
             _BBBBBBBBBBBB_
             ______________
         ''', '''
           <style>
             @page { size: 14px 10px }
             html { background: #fff }
             body { margin: 1px; height: 8px;
                    /* Use nearest neighbor algorithm for image resizing: */
                    image-rendering: pixelated;
                    background: url(pattern.png) no-repeat right 0/cover }
           </style>
           <body>'''),
    )
)
def test_background_size(name, expected_width, expected_height,
                         expected_pixels, html):
    assert_pixels(
        name, expected_width, expected_height, expected_pixels, html)
