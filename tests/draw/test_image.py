"""Test how images are drawn."""

import pytest

from ..testing_utils import FakeHTML, assert_no_logs, capture_logs, resource_path

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

centered_image_overflow = '''
    ________
    ________
    __rBBBBB
    __BBBBBB
    __BBBBBB
    __BBBBBB
    __BBBBBB
    __BBBBBB
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

border_image = '''
    ________
    _GGGGGG_
    _GrBBBG_
    _GBBBBG_
    _GBBBBG_
    _GBBBBG_
    _GGGGGG_
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
def test_images(assert_pixels, filename, image):
    assert_pixels(image, '''
      <style>
        @page { size: 8px }
        body { margin: 2px 0 0 2px; font-size: 0 }
        img { overflow: hidden }
      </style>
      <div><img src="%s"></div>''' % filename)


@assert_no_logs
@pytest.mark.parametrize('filename', (
    'pattern.svg',
    'pattern.png',
    'pattern.palette.png',
    'pattern.gif',
))
def test_resized_images(assert_pixels, filename):
    assert_pixels(resized_image, '''
      <style>
        @page { size: 12px }
        body { margin: 2px 0 0 2px; font-size: 0 }
        img { display: block; width: 8px; image-rendering: pixelated;
              overflow: hidden }
      </style>
      <div><img src="%s"></div>''' % filename)


def test_image_overflow(assert_pixels):
    assert_pixels(centered_image_overflow, '''
      <style>
        @page { size: 8px }
        body { margin: 2px 0 0 2px; font-size: 0 }
      </style>
      <div><img src="pattern.svg"></div>''')


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
def test_svg_sizing(assert_pixels, viewbox, width, height):
    assert_pixels(centered_image, '''
      <style>
        @page { size: 8px }
        body { margin: 2px 0 0 2px; font-size: 0 }
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
def test_svg_resizing(assert_pixels, viewbox, width, height, image):
    assert_pixels(image, '''
      <style>
        @page { size: 12px }
        body { margin: 2px 0 0 2px; font-size: 0 }
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
def test_images_block(assert_pixels):
    assert_pixels(centered_image, '''
      <style>
        @page { size: 8px }
        body { margin: 0; font-size: 0 }
        img { display: block; margin: 2px auto 0 }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_images_not_found(assert_pixels):
    with capture_logs() as logs:
        assert_pixels(no_image, '''
          <style>
            @page { size: 8px }
            body { margin: 0; font-size: 0 }
            img { display: block; margin: 2px auto 0 }
          </style>
          <div><img src="inexistent1.png" alt=""></div>''')
    assert len(logs) == 1
    assert 'ERROR: Failed to load image' in logs[0]
    assert 'inexistent1.png' in logs[0]


@assert_no_logs
def test_images_no_src(assert_pixels):
    assert_pixels(no_image, '''
      <style>
        @page { size: 8px }
        body { margin: 0; font-size: 0 }
        img { display: block; margin: 2px auto 0 }
      </style>
      <div><img alt=""></div>''')


@assert_no_logs
def test_images_alt(assert_same_renderings):
    with capture_logs() as logs:
        documents = (
            '''
              <style>
                @page { size: 200px 30px }
                body { margin: 0; font-size: 0 }
              </style>
              <div>%s</div>''' % html
            for html in (
                'Hello',
                '<img src="inexistent2.png" alt="Hello">',
                '<img alt="Hello">',
                '<img src="data:image/svg+xml,<svg></svg>" alt="Hello">',
            ))
        assert_same_renderings(*documents)
    assert len(logs) == 1
    assert 'ERROR: Failed to load image' in logs[0]
    assert 'inexistent2.png' in logs[0]


@assert_no_logs
def test_images_repeat_transparent(assert_pixels):
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/1440
    assert_pixels('_\n_\n_', '''
      <style>
        @page { size: 1px }
        div { height: 100px; width: 100px; background: url(logo_small.png) }
      </style>
      <div></div><div></div><div></div>''')


@assert_no_logs
def test_images_no_width(assert_pixels):
    assert_pixels(no_image, '''
      <style>
        @page { size: 8px }
        body { margin: 2px; font-size: 0 }
      </style>
      <div><img src="pattern.png" alt="not shown"
                style="width: 0; height: 1px"></div>''')


@assert_no_logs
def test_images_no_height(assert_pixels):
    assert_pixels(no_image, '''
      <style>
        @page { size: 8px }
        body { margin: 2px; font-size: 0 }
      </style>
      <div><img src="pattern.png" alt="not shown"
                style="width: 1px; height: 0"></div>''')


@assert_no_logs
def test_images_no_width_height(assert_pixels):
    assert_pixels(no_image, '''
      <style>
        @page { size: 8px }
        body { margin: 2px; font-size: 0 }
      </style>
      <div><img src="pattern.png" alt="not shown"
                style="width: 0; height: 0"></div>''')


@assert_no_logs
def test_images_page_break(assert_pixels):
    assert_pixels(page_break, '''
      <style>
        @page { size: 8px; margin: 2px }
        body { font-size: 0 }
      </style>
      <div><img src="pattern.png"></div>
      <div style="page-break-before: right"><img src="pattern.png"></div>''')


@assert_no_logs
def test_image_repeat_inline(assert_pixels):
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/808
    assert_pixels(table, '''
      <style>
        @page { size: 8px; margin: 0 }
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
def test_image_repeat_block(assert_pixels):
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/808
    assert_pixels(table, '''
      <style>
        @page { size: 8px; margin: 0 }
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
def test_images_padding(assert_pixels):
    # Regression test: padding used to be ignored on images
    assert_pixels(centered_image, '''
      <style>
        @page { size: 8px }
        body { font-size: 0 }
      </style>
      <div style="line-height: 1px">
        <img src=pattern.png style="padding: 2px 0 0 2px">
      </div>''')


@assert_no_logs
def test_images_in_inline_block(assert_pixels):
    # Regression test: this used to cause an exception
    assert_pixels(centered_image, '''
      <style>
        @page { size: 8px }
        body { margin: 2px 0 0 2px; font-size: 0 }
      </style>
      <div style="display: inline-block">
        <p><img src=pattern.png></p>
      </div>''')


@assert_no_logs
def test_images_transparent_text(assert_pixels):
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/2131
    assert_pixels(centered_image, '''<style>
        @page { size: 8px }
        body { margin: 2px 0 0 2px; font-size: 2px; line-height: 0 }
      </style>
      <div style="color: #0001">123</div>
      <img src=pattern.png>
    ''')


@assert_no_logs
def test_images_shared_pattern(assert_pixels):
    # The same image is used in a repeating background,
    # then in a non-repating <img>.
    # If Pattern objects are shared carelessly, the image will be repeated.
    assert_pixels('''
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
        body { margin: 2px; font-size: 0 }
      </style>
      <div style="background: url(blue.jpg);
                  height: 2px; margin-bottom: 1px"></div>
      <img src=blue.jpg>
    ''')


@assert_no_logs
def test_image_resolution(assert_same_renderings):
    assert_same_renderings(
        '''
            <style>@page { size: 20px; margin: 2px }</style>
            <div style="font-size: 0">
                <img src="pattern.png" style="width: 8px"></div>
        ''',
        '''
            <style>@page { size: 20px; margin: 2px }</style>
            <div style="image-resolution: .5dppx; font-size: 0">
                <img src="pattern.png"></div>
        ''',
        '''
            <style>@page { size: 20px; margin: 2px }
                   div::before { content: url(pattern.png) }
            </style>
            <div style="image-resolution: .5dppx; font-size: 0"></div>
        ''',
        '''
            <style>@page { size: 20px; margin: 2px }
            </style>
            <div style="height: 16px; image-resolution: .5dppx;
                        background: url(pattern.png) no-repeat"></div>
        ''',
    )


@assert_no_logs
def test_image_cover(assert_pixels):
    assert_pixels(cover_image, '''
      <style>
        @page { size: 8px }
        body { margin: 2px 0 0 2px; font-size: 0 }
        img { object-fit: cover; height: 4px; width: 2px; overflow: hidden }
      </style>
      <img src="pattern.png">''')


@assert_no_logs
def test_image_contain(assert_pixels):
    assert_pixels(centered_image, '''
      <style>
        @page { size: 8px }
        body { margin: 1px 0 0 2px; font-size: 0 }
        img { object-fit: contain; height: 6px; width: 4px; overflow: hidden }
      </style>
      <img src="pattern.png">''')


@assert_no_logs
def test_image_none(assert_pixels):
    assert_pixels(centered_image, '''
      <style>
        @page { size: 8px }
        body { margin: 1px 0 0 1px; font-size: 0 }
        img { object-fit: none; height: 6px; width: 6px }
      </style>
      <img src="pattern.png">''')


@assert_no_logs
def test_image_scale_down(assert_pixels):
    assert_pixels(centered_image, '''
      <style>
        @page { size: 8px }
        body { margin: 1px 0 0 1px; font-size: 0 }
        img { object-fit: scale-down; height: 6px; width: 6px }
      </style>
      <img src="pattern.png">''')


@assert_no_logs
def test_image_position(assert_pixels):
    assert_pixels(centered_image, '''
      <style>
        @page { size: 8px }
        body { margin: 1px 0 0 1px; font-size: 0 }
        img { object-fit: none; height: 6px; width: 6px;
              object-position: bottom 50% right 50% }
      </style>
      <img src="pattern.png">''')


@assert_no_logs
def test_images_border(assert_pixels):
    assert_pixels(border_image, '''
      <style>
        @page { size: 8px }
        body { margin: 0; font-size: 0 }
        img { margin: 1px; border: 1px solid lime }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_images_border_absolute(assert_pixels):
    assert_pixels(border_image, '''
      <style>
        @page { size: 8px }
        body { margin: 0; font-size: 0 }
        img { margin: 1px; border: 1px solid lime; position: absolute }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_image_exif(assert_same_renderings):
    assert_same_renderings(
        '''
            <style>@page { size: 10px }</style>
            <img style="display: block" src="not-optimized.jpg">
        ''',
        '''
            <style>@page { size: 10px }</style>
            <img style="display: block" src="not-optimized-exif.jpg">
        ''',
        tolerance=25,
    )


@assert_no_logs
def test_image_exif_image_orientation(assert_same_renderings):
    assert_same_renderings(
        '''
            <style>@page { size: 10px }</style>
            <img style="display: block; image-orientation: 180deg"
                 src="not-optimized-exif.jpg">
        ''',
        '''
            <style>@page { size: 10px }</style>
            <img style="display: block" src="not-optimized-exif.jpg">
        ''',
        tolerance=25,
    )


@assert_no_logs
def test_image_exif_image_orientation_keep_format():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/1755
    pdf = FakeHTML(
        string='''
          <style>@page { size: 10px }</style>
          <img style="display: block; image-orientation: 180deg"
               src="not-optimized-exif.jpg">''',
        base_url=resource_path('<inline HTML>')).write_pdf()
    assert b'DCTDecode' in pdf
