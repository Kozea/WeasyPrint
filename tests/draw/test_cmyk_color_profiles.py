"""Test CMYK and Color Profiles."""

from ..testing_utils import assert_no_logs


@assert_no_logs
def test_device_cmyk_with_icc(assert_pixels):
    assert_pixels('PP\nPP', '''
      <style>
        @color-profile device-cmyk {
          src: url(cmyk.icc);
          components: C, M, Y, K;
        }
        @page { size: 2px }
        html, body { height: 100%; margin: 0 }
        html { background: device-cmyk(0.8 0.6 0.4 0.2) }
      </style>
      <body>''')


@assert_no_logs
def test_device_cmyk_without_icc(assert_pixels):
    assert_pixels('QQ\nQQ', '''
      <style>
        @page { size: 2px }
        html, body { height: 100%; margin: 0 }
        html { background: device-cmyk(0.8 0.6 0.4 0.2) }
      </style>
      <body>''')


@assert_no_logs
def test_custom_cmyk_with_icc(assert_pixels):
    assert_pixels('PP\nPP', '''
      <style>
        @color-profile --custom-cmyk {
          src: url(cmyk.icc);
          components: C, M, Y, K;
        }
        @page { size: 2px }
        html, body { height: 100%; margin: 0 }
        html { background: color(--custom-cmyk 0.8 0.6 0.4 0.2) }
      </style>
      <body>''')


@assert_no_logs
def test_image_cmyk_without_icc(assert_pixels):
    assert_pixels('QQ\nQQ', '''
      <style>
        @page { size: 2px }
        img { display: block; }
      </style>
      <img src="cmyk_without_icc.jpg">''')


@assert_no_logs
def test_image_cmyk_with_external_icc(assert_pixels):
    assert_pixels('PP\nPP', '''
      <style>
        @color-profile device-cmyk {
          src: url(cmyk.icc);
          components: C, M, Y, K;
        }
        @page { size: 2px }
        img { display: block; }
      </style>
      <img src="cmyk_without_icc.jpg">''')


@assert_no_logs
def test_image_cmyk_with_icc(assert_pixels):
    assert_pixels('QQ\nQQ', '''
      <style>
        @page { size: 2px }
        img { display: block; }
      </style>
      <img src="cmyk_with_icc.jpg">''')
