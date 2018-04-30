"""
    weasyprint.tests.layout.image
    -----------------------------

    Tests for image layout.

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import pytest

from ...formatting_structure import boxes
from ..test_boxes import render_pages as parse
from ..testing_utils import assert_no_logs, capture_logs, requires


def get_img(html):
    page, = parse(html)
    html, = page.children
    body, = html.children
    line, = body.children
    img, = line.children
    return body, img


@assert_no_logs
def test_images_1():
    # Try a few image formats
    for html in [
        '<img src="%s">' % url for url in [
            'pattern.png', 'pattern.gif', 'blue.jpg', 'pattern.svg',
            "data:image/svg+xml,<svg width='4' height='4'></svg>",
            "DatA:image/svg+xml,<svg width='4px' height='4px'></svg>",
        ]
    ] + [
        '<embed src=pattern.png>',
        '<embed src=pattern.svg>',
        '<embed src=really-a-png.svg type=image/png>',
        '<embed src=really-a-svg.png type=image/svg+xml>',

        '<object data=pattern.png>',
        '<object data=pattern.svg>',
        '<object data=really-a-png.svg type=image/png>',
        '<object data=really-a-svg.png type=image/svg+xml>',
    ]:
        body, img = get_img(html)
        assert img.width == 4
        assert img.height == 4


@assert_no_logs
def test_images_2():
    # With physical units
    url = "data:image/svg+xml,<svg width='2.54cm' height='0.5in'></svg>"
    body, img = get_img('<img src="%s">' % url)
    assert img.width == 96
    assert img.height == 48


@requires('cairo', (1, 15, 12))
@assert_no_logs
def test_images_3():
    # Invalid images
    for url in [
        'nonexistent.png',
        'unknownprotocol://weasyprint.org/foo.png',
        'data:image/unknowntype,Not an image',
        # Invalid protocol
        'datå:image/svg+xml,<svg width="4" height="4"></svg>',
        # zero-byte images
        'data:image/png,',
        'data:image/jpeg,',
        'data:image/svg+xml,',
        # Incorrect format
        'data:image/png,Not a PNG',
        'data:image/jpeg,Not a JPEG',
        'data:image/svg+xml,<svg>invalid xml',
        # Explicit SVG, no sniffing
        'data:image/svg+xml;base64,'
        'R0lGODlhAQABAIABAP///wAAACwAAAAAAQABAAACAkQBADs=',
        'really-a-png.svg',
    ]:
        with capture_logs() as logs:
            body, img = get_img("<img src='%s' alt='invalid image'>" % url)
        assert len(logs) == 1
        assert 'ERROR: Failed to load image' in logs[0]
        assert isinstance(img, boxes.InlineBox)  # not a replaced box
        text, = img.children
        assert text.text == 'invalid image', url


@requires('cairo', (1, 15, 12))
@assert_no_logs
def test_images_4():
    # Format sniffing
    for url in [
        # GIF with JPEG mimetype
        'data:image/jpeg;base64,'
        'R0lGODlhAQABAIABAP///wAAACwAAAAAAQABAAACAkQBADs=',
        # GIF with PNG mimetype
        'data:image/png;base64,'
        'R0lGODlhAQABAIABAP///wAAACwAAAAAAQABAAACAkQBADs=',
        # PNG with JPEG mimetype
        'data:image/jpeg;base64,'
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC'
        '0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
        # SVG with PNG mimetype
        'data:image/png,<svg width="1" height="1"></svg>',
        'really-a-svg.png',
    ]:
        with capture_logs() as logs:
            body, img = get_img("<img src='%s'>" % url)
        assert len(logs) == 0


@assert_no_logs
def test_images_5():
    with capture_logs() as logs:
        parse('<img src=nonexistent.png><img src=nonexistent.png>')
    # Failures are cached too: only one error
    assert len(logs) == 1
    assert 'ERROR: Failed to load image' in logs[0]


@assert_no_logs
def test_images_6():
    # Layout rules try to preserve the ratio, so the height should be 40px too:
    body, img = get_img('''<body style="font-size: 0">
        <img src="pattern.png" style="width: 40px">''')
    assert body.height == 40
    assert img.position_y == 0
    assert img.width == 40
    assert img.height == 40


@assert_no_logs
def test_images_7():
    body, img = get_img('''<body style="font-size: 0">
        <img src="pattern.png" style="height: 40px">''')
    assert body.height == 40
    assert img.position_y == 0
    assert img.width == 40
    assert img.height == 40


@assert_no_logs
def test_images_8():
    # Same with percentages
    body, img = get_img('''<body style="font-size: 0"><p style="width: 200px">
        <img src="pattern.png" style="width: 20%">''')
    assert body.height == 40
    assert img.position_y == 0
    assert img.width == 40
    assert img.height == 40


@assert_no_logs
def test_images_9():
    body, img = get_img('''<body style="font-size: 0">
        <img src="pattern.png" style="min-width: 40px">''')
    assert body.height == 40
    assert img.position_y == 0
    assert img.width == 40
    assert img.height == 40


@assert_no_logs
def test_images_10():
    body, img = get_img('<img src="pattern.png" style="max-width: 2px">')
    assert img.width == 2
    assert img.height == 2


@assert_no_logs
def test_images_11():
    # display: table-cell is ignored. XXX Should it?
    page, = parse('''<body style="font-size: 0">
        <img src="pattern.png" style="width: 40px">
        <img src="pattern.png" style="width: 60px; display: table-cell">
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    assert body.height == 60
    assert img_1.width == 40
    assert img_1.height == 40
    assert img_2.width == 60
    assert img_2.height == 60
    assert img_1.position_y == 20
    assert img_2.position_y == 0


@assert_no_logs
def test_images_12():
    # Block-level image:
    page, = parse('''
        <style>
            @page { size: 100px }
            img { width: 40px; margin: 10px auto; display: block }
        </style>
        <body>
            <img src="pattern.png">
    ''')
    html, = page.children
    body, = html.children
    img, = body.children
    assert img.element_tag == 'img'
    assert img.position_x == 0
    assert img.position_y == 0
    assert img.width == 40
    assert img.height == 40
    assert img.content_box_x() == 30  # (100 - 40) / 2 == 30px for margin-left
    assert img.content_box_y() == 10


@assert_no_logs
def test_images_13():
    page, = parse('''
        <style>
            @page { size: 100px }
            img { min-width: 40%; margin: 10px auto; display: block }
        </style>
        <body>
            <img src="pattern.png">
    ''')
    html, = page.children
    body, = html.children
    img, = body.children
    assert img.element_tag == 'img'
    assert img.position_x == 0
    assert img.position_y == 0
    assert img.width == 40
    assert img.height == 40
    assert img.content_box_x() == 30  # (100 - 40) / 2 == 30px for margin-left
    assert img.content_box_y() == 10


@assert_no_logs
def test_images_14():
    page, = parse('''
        <style>
            @page { size: 100px }
            img { min-width: 40px; margin: 10px auto; display: block }
        </style>
        <body>
            <img src="pattern.png">
    ''')
    html, = page.children
    body, = html.children
    img, = body.children
    assert img.element_tag == 'img'
    assert img.position_x == 0
    assert img.position_y == 0
    assert img.width == 40
    assert img.height == 40
    assert img.content_box_x() == 30  # (100 - 40) / 2 == 30px for margin-left
    assert img.content_box_y() == 10


@assert_no_logs
def test_images_15():
    page, = parse('''
        <style>
            @page { size: 100px }
            img { min-height: 30px; max-width: 2px;
                  margin: 10px auto; display: block }
        </style>
        <body>
            <img src="pattern.png">
    ''')
    html, = page.children
    body, = html.children
    img, = body.children
    assert img.element_tag == 'img'
    assert img.position_x == 0
    assert img.position_y == 0
    assert img.width == 2
    assert img.height == 30
    assert img.content_box_x() == 49  # (100 - 2) / 2 == 49px for margin-left
    assert img.content_box_y() == 10


@assert_no_logs
def test_images_16():
    page, = parse('''
        <body style="float: left">
        <img style="height: 200px; margin: 10px; display: block" src="
            data:image/svg+xml,
            <svg width='150' height='100'></svg>
        ">
    ''')
    html, = page.children
    body, = html.children
    img, = body.children
    assert body.width == 320
    assert body.height == 220
    assert img.element_tag == 'img'
    assert img.width == 300
    assert img.height == 200


@assert_no_logs
def test_linear_gradient():
    red = (1, 0, 0, 1)
    lime = (0, 1, 0, 1)
    blue = (0, 0, 1, 1)

    def layout(gradient_css, type_='linear', init=(),
               positions=[0, 1], colors=[blue, lime], scale=(1, 1)):
        page, = parse('<style>@page { background: ' + gradient_css)
        layer, = page.background.layers
        scale_x, scale_y = scale
        result = layer.image.layout(
            400, 300, lambda dx, dy: (dx * scale_x, dy * scale_y))
        assert result[0] == 1
        assert result[1] == type_
        assert result[2] == pytest.approx(init)
        assert result[3] == pytest.approx(positions)
        assert result[4] == colors

    layout('linear-gradient(blue)', 'solid', blue, [], [])
    layout('repeating-linear-gradient(blue)', 'solid', blue, [], [])
    layout('repeating-linear-gradient(blue, lime 1.5px)',
           'solid', (0, .5, .5, 1), [], [])
    layout('linear-gradient(blue, lime)', init=(200, 0, 200, 300))
    layout('repeating-linear-gradient(blue, lime)', init=(200, 0, 200, 300))
    layout('repeating-linear-gradient(blue, lime 20px)',
           init=(200, 0, 200, 20))
    layout('repeating-linear-gradient(blue, lime 20px)',
           'solid', (0, .5, .5, 1), [], [], scale=(1 / 20, 1 / 20))

    layout('linear-gradient(to bottom, blue, lime)', init=(200, 0, 200, 300))
    layout('linear-gradient(to top, blue, lime)', init=(200, 300, 200, 0))
    layout('linear-gradient(to right, blue, lime)', init=(0, 150, 400, 150))
    layout('linear-gradient(to left, blue, lime)', init=(400, 150, 0, 150))

    layout('linear-gradient(to top left, blue, lime)',
           init=(344, 342, 56, -42))
    layout('linear-gradient(to top right, blue, lime)',
           init=(56, 342, 344, -42))
    layout('linear-gradient(to bottom left, blue, lime)',
           init=(344, -42, 56, 342))
    layout('linear-gradient(to bottom right, blue, lime)',
           init=(56, -42, 344, 342))

    layout('linear-gradient(270deg, blue, lime)', init=(400, 150, 0, 150))
    layout('linear-gradient(.75turn, blue, lime)', init=(400, 150, 0, 150))
    layout('linear-gradient(45deg, blue, lime)', init=(25, 325, 375, -25))
    layout('linear-gradient(.125turn, blue, lime)', init=(25, 325, 375, -25))
    layout('linear-gradient(.375turn, blue, lime)', init=(25, -25, 375, 325))
    layout('linear-gradient(.625turn, blue, lime)', init=(375, -25, 25, 325))
    layout('linear-gradient(.875turn, blue, lime)', init=(375, 325, 25, -25))

    layout('linear-gradient(blue 2em, lime 20%)', init=(200, 32, 200, 60))
    layout('linear-gradient(blue 100px, red, blue, red 160px, lime)',
           init=(200, 100, 200, 300), colors=[blue, red, blue, red, lime],
           positions=[0, .1, .2, .3, 1])
    layout('linear-gradient(blue -100px, blue 0, red -12px, lime 50%)',
           init=(200, -100, 200, 150), colors=[blue, blue, red, lime],
           positions=[0, .4, .4, 1])
    layout('linear-gradient(blue, blue, red, lime -7px)',
           init=(200, 0, 200, 100), colors=[blue, blue, red, lime],
           positions=[0, 0, 0, 0])
    layout('repeating-linear-gradient(blue, blue, lime, lime -7px)',
           'solid', (0, .5, .5, 1), [], [])


@assert_no_logs
def test_radial_gradient():
    red = (1, 0, 0, 1)
    lime = (0, 1, 0, 1)
    blue = (0, 0, 1, 1)

    def layout(gradient_css, type_='radial', init=(),
               positions=[0, 1], colors=[blue, lime], scale_y=1,
               ctm_scale=(1, 1)):
        if type_ == 'radial':
            center_x, center_y, radius0, radius1 = init
            init = (center_x, center_y / scale_y, radius0,
                    center_x, center_y / scale_y, radius1)
        page, = parse('<style>@page { background: ' + gradient_css)
        layer, = page.background.layers
        ctm_scale_x, ctm_scale_y = ctm_scale
        result = layer.image.layout(
            400, 300, lambda dx, dy: (dx * ctm_scale_x, dy * ctm_scale_y))
        assert result[0] == scale_y
        assert result[1] == type_
        assert result[2] == pytest.approx(init)
        assert result[3] == pytest.approx(positions)
        assert result[4] == colors

    layout('radial-gradient(blue)', 'solid', blue, [], [])
    layout('repeating-radial-gradient(blue)', 'solid', blue, [], [])
    layout('radial-gradient(100px, blue, lime)',
           init=(200, 150, 0, 100))

    layout('radial-gradient(100px at right 20px bottom 30px, lime, red)',
           init=(380, 270, 0, 100), colors=[lime, red])
    layout('radial-gradient(0 0, blue, lime)',
           init=(200, 150, 0, 1e-7))
    layout('radial-gradient(1px 0, blue, lime)',
           init=(200, 150, 0, 1e7), scale_y=1e-14)
    layout('radial-gradient(0 1px, blue, lime)',
           init=(200, 150, 0, 1e-7), scale_y=1e14)
    layout('repeating-radial-gradient(20px 40px, blue, lime)',
           init=(200, 150, 0, 20), scale_y=(40 / 20))
    layout('repeating-radial-gradient(20px 40px, blue, lime)',
           init=(200, 150, 0, 20), scale_y=(40 / 20), ctm_scale=(1 / 9, 1))
    layout('repeating-radial-gradient(20px 40px, blue, lime)',
           init=(200, 150, 0, 20), scale_y=(40 / 20), ctm_scale=(1, 1 / 19))
    layout('repeating-radial-gradient(20px 40px, blue, lime)',
           'solid', (0, .5, .5, 1), [], [], ctm_scale=((1 / 11), 1))
    layout('repeating-radial-gradient(20px 40px, blue, lime)',
           'solid', (0, .5, .5, 1), [], [], ctm_scale=(1, (1 / 21)))
    layout('repeating-radial-gradient(42px, blue -20px, lime 10px)',
           init=(200, 150, 10, 40))
    layout('repeating-radial-gradient(42px, blue -140px, lime -110px)',
           init=(200, 150, 10, 40))
    layout('radial-gradient(42px, blue -20px, lime -1px)',
           'solid', lime, [], [])
    layout('radial-gradient(42px, blue -20px, lime 0)',
           'solid', lime, [], [])
    layout('radial-gradient(42px, blue -20px, lime 20px)',
           init=(200, 150, 0, 20), colors=[(0, .5, .5, 1), lime])

    layout('radial-gradient(100px 120px, blue, lime)',
           init=(200, 150, 0, 100), scale_y=(120 / 100))
    layout('radial-gradient(25% 40%, blue, lime)',
           init=(200, 150, 0, 100), scale_y=(120 / 100))

    layout('radial-gradient(circle closest-side, blue, lime)',
           init=(200, 150, 0, 150))
    layout('radial-gradient(circle closest-side at 150px 50px, blue, lime)',
           init=(150, 50, 0, 50))
    layout('radial-gradient(circle closest-side at 45px 50px, blue, lime)',
           init=(45, 50, 0, 45))
    layout('radial-gradient(circle closest-side at 420px 50px, blue, lime)',
           init=(420, 50, 0, 20))
    layout('radial-gradient(circle closest-side at 420px 281px, blue, lime)',
           init=(420, 281, 0, 19))

    layout('radial-gradient(closest-side, blue 20%, lime)',
           init=(200, 150, 40, 200), scale_y=(150 / 200))
    layout('radial-gradient(closest-side at 300px 20%, blue, lime)',
           init=(300, 60, 0, 100), scale_y=(60 / 100))
    layout('radial-gradient(closest-side at 10% 230px, blue, lime)',
           init=(40, 230, 0, 40), scale_y=(70 / 40))

    layout('radial-gradient(circle farthest-side, blue, lime)',
           init=(200, 150, 0, 200))
    layout('radial-gradient(circle farthest-side at 150px 50px, blue, lime)',
           init=(150, 50, 0, 250))
    layout('radial-gradient(circle farthest-side at 45px 50px, blue, lime)',
           init=(45, 50, 0, 355))
    layout('radial-gradient(circle farthest-side at 420px 50px, blue, lime)',
           init=(420, 50, 0, 420))
    layout('radial-gradient(circle farthest-side at 220px 310px, blue, lime)',
           init=(220, 310, 0, 310))

    layout('radial-gradient(farthest-side, blue, lime)',
           init=(200, 150, 0, 200), scale_y=(150 / 200))
    layout('radial-gradient(farthest-side at 300px 20%, blue, lime)',
           init=(300, 60, 0, 300), scale_y=(240 / 300))
    layout('radial-gradient(farthest-side at 10% 230px, blue, lime)',
           init=(40, 230, 0, 360), scale_y=(230 / 360))

    layout('radial-gradient(circle closest-corner, blue, lime)',
           init=(200, 150, 0, 250))
    layout('radial-gradient(circle closest-corner at 340px 80px, blue, lime)',
           init=(340, 80, 0, 100))
    layout('radial-gradient(circle closest-corner at 0 342px, blue, lime)',
           init=(0, 342, 0, 42))

    layout('radial-gradient(closest-corner, blue, lime)',
           init=(200, 150, 0, 200 * 2 ** 0.5), scale_y=(150 / 200))
    layout('radial-gradient(closest-corner at 450px 100px, blue, lime)',
           init=(450, 100, 0, 50 * 2 ** 0.5), scale_y=(100 / 50))
    layout('radial-gradient(closest-corner at 40px 210px, blue, lime)',
           init=(40, 210, 0, 40 * 2 ** 0.5), scale_y=(90 / 40))

    layout('radial-gradient(circle farthest-corner, blue, lime)',
           init=(200, 150, 0, 250))
    layout('radial-gradient(circle farthest-corner'
           ' at 300px -100px, blue, lime)',
           init=(300, -100, 0, 500))
    layout('radial-gradient(circle farthest-corner at 400px 0, blue, lime)',
           init=(400, 0, 0, 500))

    layout('radial-gradient(farthest-corner, blue, lime)',
           init=(200, 150, 0, 200 * 2 ** 0.5), scale_y=(150 / 200))
    layout('radial-gradient(farthest-corner at 450px 100px, blue, lime)',
           init=(450, 100, 0, 450 * 2 ** 0.5), scale_y=(200 / 450))
    layout('radial-gradient(farthest-corner at 40px 210px, blue, lime)',
           init=(40, 210, 0, 360 * 2 ** 0.5), scale_y=(210 / 360))
