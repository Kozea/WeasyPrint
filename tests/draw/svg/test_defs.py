"""Test how SVG definitions are drawn."""

from base64 import b64encode

from ...testing_utils import assert_no_logs

SVG = '''
<svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <rect id="rectangle" width="5" height="2" fill="red" />
    <symbol id="square">
      <rect width="2" height="2" fill="blue" />
    </symbol>
  </defs>
  <use href="#rectangle" />
  <use href="#square" x="3" y="3" />
  <use href="#rectangle" x="5" y="6" />
</svg>
'''

RESULT = '''
  RRRRR_____
  RRRRR_____
  __________
  ___BB_____
  ___BB_____
  __________
  _____RRRRR
  _____RRRRR
  __________
  __________
'''


@assert_no_logs
def test_use(assert_pixels):
    assert_pixels(RESULT, '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
    ''' + SVG)


@assert_no_logs
def test_use_base64(assert_pixels):
    base64_svg = b64encode(SVG.encode()).decode()
    assert_pixels(RESULT, '''
      <style>
        @page { size: 10px }
        img { display: block }
      </style>
      <img src="data:image/svg+xml;base64,''' + base64_svg + '"/>')
