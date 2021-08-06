"""
    weasyprint.tests.test_draw.test_image
    -------------------------------------

    Test how images are drawn.

"""

import pytest

from ..testing_utils import assert_no_logs, capture_logs
from . import assert_pixels, assert_same_rendering

centered_image = '''
    ________
    ________
    __rBBB__
    __BBBB__
    __BBBB__
    __BBBB__
    ________
    ________
'''

resized_image = '''
    ____________
    ____________
    __rrBBBBBB__
    __rrBBBBBB__
    __BBBBBBBB__
    __BBBBBBBB__
    __BBBBBBBB__
    __BBBBBBBB__
    __BBBBBBBB__
    __BBBBBBBB__
    ____________
    ____________
'''

small_resized_image = '''
    ____________
    ____________
    __rBBB______
    __BBBB______
    __BBBB______
    __BBBB______
    ____________
    ____________
    ____________
    ____________
    ____________
    ____________
'''

blue_image = '''
    ________
    ________
    __aaaa__
    __aaaa__
    __aaaa__
    __aaaa__
    ________
    ________
'''

no_image = '''
    ________
    ________
    ________
    ________
    ________
    ________
    ________
    ________
'''

page_break = '''
    ________
    ________
    __rBBB__
    __BBBB__
    __BBBB__
    __BBBB__
    ________
    ________

    ________
    ________
    ________
    ________
    ________
    ________
    ________
    ________

    ________
    ________
    __rBBB__
    __BBBB__
    __BBBB__
    __BBBB__
    ________
    ________
'''

table = '''
    ________
    ________
    __rBBB__
    __BBBB__
    __BBBB__
    __BBBB__
    ________
    ________

    __rBBB__
    __BBBB__
    __BBBB__
    __BBBB__
    ________
    ________
    ________
    ________
'''

cover_image = '''
    ________
    ________
    __BB____
    __BB____
    __BB____
    __BB____
    ________
    ________
'''


@assert_no_logs
@pytest.mark.parametrize('filename, image', (
    ('pattern.svg', centered_image),
    ('pattern.png', centered_image),
    ('pattern.palette.png', centered_image),
    ('pattern.gif', centered_image),
    ('blue.jpg', blue_image)
))
def test_images(filename, image):
    assert_pixels(f'inline_image_{filename}', 8, 8, image, '''
      <style>
        @page { size: 8px }
        body { margin: 2px 0 0 2px; background: #fff; font-size: 0 }
      </style>
      <div><img src="%s"></div>''' % filename)


@assert_no_logs
@pytest.mark.parametrize('filename', (
    'pattern.svg',
    'pattern.png',
    'pattern.palette.png',
    'pattern.gif',
))
def test_resized_images(filename):
    assert_pixels(f'resized_image_{filename}', 12, 12, resized_image, '''
      <style>
        @page { size: 12px }
        body { margin: 2px 0 0 2px; background: #fff; font-size: 0 }
        img { display: block; width: 8px; image-rendering: pixelated }
      </style>
      <div><img src="%s"></div>''' % filename)


@assert_no_logs
@pytest.mark.parametrize('viewbox, width, height', (
    (None, None, None),
    (None, 4, None),
    (None, None, 4),
    (None, 4, 4),
    ('0 0 4 4', 4, None),
    ('0 0 4 4', None, 4),
    ('0 0 4 4', 4, 4),
    ('0 0 4 4', 4, 4),
))
def test_svg_sizing(viewbox, width, height):
    assert_pixels(
        f'svg_sizing_{viewbox}_{width}_{height}', 8, 8,
        centered_image, '''
      <style>
        @page { size: 8px }
        body { margin: 2px 0 0 2px; background: #fff; font-size: 0 }
        svg { display: block }
      </style>
      <svg %s %s %s>
        <rect width="4px" height="4px" fill="#00f" />
        <rect width="1px" height="1px" fill="#f00" />
      </svg>''' % (
          f'width="{width}"' if width else '',
          f'height="{height}px"' if height else '',
          f'viewbox="{viewbox}"' if viewbox else ''))


@assert_no_logs
@pytest.mark.parametrize('viewbox, width, height, image', (
    (None, None, None, small_resized_image),
    (None, 8, None, small_resized_image),
    (None, None, 8, small_resized_image),
    (None, 8, 8, small_resized_image),
    ('0 0 4 4', None, None, resized_image),
    ('0 0 4 4', 8, None, resized_image),
    ('0 0 4 4', None, 8, resized_image),
    ('0 0 4 4', 8, 8, resized_image),
    ('0 0 4 4', 800, 800, resized_image),
))
def test_svg_resizing(viewbox, width, height, image):
    assert_pixels(
        f'svg_resizing_{viewbox}_{width}_{height}', 12, 12, image, '''
      <style>
        @page { size: 12px }
        body { margin: 2px 0 0 2px; background: #fff; font-size: 0 }
        svg { display: block; width: 8px }
      </style>
      <svg %s %s %s>
        <rect width="4" height="4" fill="#00f" />
        <rect width="1" height="1" fill="#f00" />
      </svg>''' % (
          f'width="{width}"' if width else '',
          f'height="{height}px"' if height else '',
          f'viewbox="{viewbox}"' if viewbox else ''))


@assert_no_logs
def test_images_block():
    assert_pixels('block_image', 8, 8, centered_image, '''
      <style>
        @page { size: 8px }
        body { margin: 0; background: #fff; font-size: 0 }
        img { display: block; margin: 2px auto 0 }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_images_not_found():
    with capture_logs() as logs:
        assert_pixels('image_not_found', 8, 8, no_image, '''
          <style>
            @page { size: 8px }
            body { margin: 0; background: #fff; font-size: 0 }
            img { display: block; margin: 2px auto 0 }
          </style>
          <div><img src="inexistent1.png" alt=""></div>''')
    assert len(logs) == 1
    assert 'ERROR: Failed to load image' in logs[0]
    assert 'inexistent1.png' in logs[0]


@assert_no_logs
def test_images_no_src():
    assert_pixels('image_no_src', 8, 8, no_image, '''
      <style>
        @page { size: 8px }
        body { margin: 0; background: #fff; font-size: 0 }
        img { display: block; margin: 2px auto 0 }
      </style>
      <div><img alt=""></div>''')


@assert_no_logs
def test_images_alt():
    with capture_logs() as logs:
        assert_same_rendering(200, 30, [
            (name, '''
              <style>
                @page { size: 200px 30px }
                body { margin: 0; background: #fff; font-size: 0 }
              </style>
              <div>%s</div>''' % html)
            for name, html in [
                ('image_alt_text_reference', 'Hello, world!'),
                ('image_alt_text_not_found',
                    '<img src="inexistent2.png" alt="Hello, world!">'),
                ('image_alt_text_no_src',
                    '<img alt="Hello, world!">'),
                ('image_svg_no_intrinsic_size',
                    '''<img src="data:image/svg+xml,<svg></svg>"
                            alt="Hello, world!">'''),
            ]
        ])
    assert len(logs) == 1
    assert 'ERROR: Failed to load image' in logs[0]
    assert 'inexistent2.png' in logs[0]


@assert_no_logs
def test_images_no_width():
    assert_pixels('image_0x1', 8, 8, no_image, '''
      <style>
        @page { size: 8px }
        body { margin: 2px; background: #fff; font-size: 0 }
      </style>
      <div><img src="pattern.png" alt="not shown"
                style="width: 0; height: 1px"></div>''')


@assert_no_logs
def test_images_no_height():
    assert_pixels('image_1x0', 8, 8, no_image, '''
      <style>
        @page { size: 8px }
        body { margin: 2px; background: #fff; font-size: 0 }
      </style>
      <div><img src="pattern.png" alt="not shown"
                style="width: 1px; height: 0"></div>''')


@assert_no_logs
def test_images_no_width_height():
    assert_pixels('image_0x0', 8, 8, no_image, '''
      <style>
        @page { size: 8px }
        body { margin: 2px; background: #fff; font-size: 0 }
      </style>
      <div><img src="pattern.png" alt="not shown"
                style="width: 0; height: 0"></div>''')


@assert_no_logs
def test_images_page_break():
    assert_pixels('image_page_break', 8, 3 * 8, page_break, '''
      <style>
        @page { size: 8px; margin: 2px; background: #fff }
        body { font-size: 0 }
      </style>
      <div><img src="pattern.png"></div>
      <div style="page-break-before: right"><img src="pattern.png"></div>''')


@assert_no_logs
def test_image_repeat_inline():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/808
    assert_pixels('image_page_repeat_inline', 8, 2 * 8, table, '''
      <style>
        @page { size: 8px; margin: 0; background: #fff }
        table { border-collapse: collapse; margin: 2px }
        th, td { border: none; padding: 0 }
        th { height: 4px; line-height: 4px }
        td { height: 2px }
        img { vertical-align: top }
      </style>
      <table>
        <thead>
          <tr><th><img src="pattern.png"></th></tr>
        </thead>
        <tbody>
          <tr><td></td></tr>
          <tr><td></td></tr>
        </tbody>
      </table>''')


@assert_no_logs
def test_image_repeat_block():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/808
    assert_pixels('image_page_repeat_block', 8, 2 * 8, table, '''
      <style>
        @page { size: 8px; margin: 0; background: #fff }
        table { border-collapse: collapse; margin: 2px }
        th, td { border: none; padding: 0 }
        th { height: 4px }
        td { height: 2px }
        img { display: block }
      </style>
      <table>
        <thead>
          <tr><th><img src="pattern.png"></th></tr>
        </thead>
        <tbody>
          <tr><td></td></tr>
          <tr><td></td></tr>
        </tbody>
      </table>''')


@assert_no_logs
def test_images_padding():
    # Regression test: padding used to be ignored on images
    assert_pixels('image_with_padding', 8, 8, centered_image, '''
      <style>
        @page { size: 8px; background: #fff }
        body { font-size: 0 }
      </style>
      <div style="line-height: 1px">
        <img src=pattern.png style="padding: 2px 0 0 2px">
      </div>''')


@assert_no_logs
def test_images_in_inline_block():
    # Regression test: this used to cause an exception
    assert_pixels('image_in_inline_block', 8, 8, centered_image, '''
      <style>
        @page { size: 8px }
        body { margin: 2px 0 0 2px; background: #fff; font-size: 0 }
      </style>
      <div style="display: inline-block">
        <p><img src=pattern.png></p>
      </div>''')


@assert_no_logs
def test_images_shared_pattern():
    # The same image is used in a repeating background,
    # then in a non-repating <img>.
    # If Pattern objects are shared carelessly, the image will be repeated.
    assert_pixels('image_shared_pattern', 12, 12, '''
        ____________
        ____________
        __aaaaaaaa__
        __aaaaaaaa__
        ____________
        __aaaa______
        __aaaa______
        __aaaa______
        __aaaa______
        ____________
        ____________
        ____________
    ''', '''
      <style>
        @page { size: 12px }
        body { margin: 2px; background: #fff; font-size: 0 }
      </style>
      <div style="background: url(blue.jpg);
                  height: 2px; margin-bottom: 1px"></div>
      <img src=blue.jpg>
    ''')


@assert_no_logs
def test_image_resolution():
    assert_same_rendering(20, 20, [
        ('image_resolution_ref', '''
            <style>@page { size: 20px; margin: 2px; background: #fff }</style>
            <div style="font-size: 0">
                <img src="pattern.png" style="width: 8px"></div>
        '''),
        ('image_resolution_img', '''
            <style>@page { size: 20px; margin: 2px; background: #fff }</style>
            <div style="image-resolution: .5dppx; font-size: 0">
                <img src="pattern.png"></div>
        '''),
        ('image_resolution_content', '''
            <style>@page { size: 20px; margin: 2px; background: #fff }
                   div::before { content: url(pattern.png) }
            </style>
            <div style="image-resolution: .5dppx; font-size: 0"></div>
        '''),
        ('image_resolution_background', '''
            <style>@page { size: 20px; margin: 2px; background: #fff }
            </style>
            <div style="height: 16px; image-resolution: .5dppx;
                        background: url(pattern.png) no-repeat"></div>
        '''),
    ])


@assert_no_logs
def test_image_cover():
    assert_pixels('image_cover', 8, 8, cover_image, '''
      <style>
        @page { size: 8px }
        body { margin: 2px 0 0 2px; background: #fff; font-size: 0 }
        img { object-fit: cover; height: 4px; width: 2px }
      </style>
      <img src="pattern.png">''')


@assert_no_logs
def test_image_contain():
    assert_pixels('image_contain', 8, 8, centered_image, '''
      <style>
        @page { size: 8px }
        body { margin: 1px 0 0 2px; background: #fff; font-size: 0 }
        img { object-fit: contain; height: 6px; width: 4px }
      </style>
      <img src="pattern.png">''')


@assert_no_logs
def test_image_none():
    assert_pixels('image_none', 8, 8, centered_image, '''
      <style>
        @page { size: 8px }
        body { margin: 1px 0 0 1px; background: #fff; font-size: 0 }
        img { object-fit: none; height: 6px; width: 6px }
      </style>
      <img src="pattern.png">''')


@assert_no_logs
def test_image_scale_down():
    assert_pixels('image_scale_down', 8, 8, centered_image, '''
      <style>
        @page { size: 8px }
        body { margin: 1px 0 0 1px; background: #fff; font-size: 0 }
        img { object-fit: scale-down; height: 6px; width: 6px }
      </style>
      <img src="pattern.png">''')


@assert_no_logs
def test_image_position():
    assert_pixels('image_position', 8, 8, centered_image, '''
      <style>
        @page { size: 8px }
        body { margin: 1px 0 0 1px; background: #fff; font-size: 0 }
        img { object-fit: none; height: 6px; width: 6px;
              object-position: bottom 50% right 50% }
      </style>
      <img src="pattern.png">''')
