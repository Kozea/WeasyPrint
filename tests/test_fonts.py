"""
    weasyprint.tests.test_fonts
    ---------------------------

    Test the fonts features.

"""

from .testing_utils import assert_no_logs, render_pages


@assert_no_logs
def test_font_face():
    page, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        body { font-family: weasyprint }
      </style>
      <span>abc</span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    assert line.width == 3 * 16


@assert_no_logs
def test_kerning_default():
    # Kerning and ligatures are on by default
    page, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        body { font-family: weasyprint }
      </style>
      <span>kk</span><span>liga</span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span1, span2 = line.children
    assert span1.width == 1.5 * 16
    assert span2.width == 1.5 * 16


@assert_no_logs
def test_kerning_deactivate():
    # Deactivate kerning
    page, = render_pages('''
      <style>
        @font-face {
          src: url(weasyprint.otf);
          font-family: no-kern;
          font-feature-settings: 'kern' off;
        }
        @font-face {
          src: url(weasyprint.otf);
          font-family: kern;
        }
        span:nth-child(1) { font-family: kern }
        span:nth-child(2) { font-family: no-kern }
      </style>
      <span>kk</span><span>kk</span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span1, span2 = line.children
    assert span1.width == 1.5 * 16
    assert span2.width == 2 * 16


@assert_no_logs
def test_kerning_ligature_deactivate():
    # Deactivate kerning and ligatures
    page, = render_pages('''
      <style>
        @font-face {
          src: url(weasyprint.otf);
          font-family: no-kern-liga;
          font-feature-settings: 'kern' off;
          font-variant: no-common-ligatures;
        }
        @font-face {
          src: url(weasyprint.otf);
          font-family: kern-liga;
        }
        span:nth-child(1) { font-family: kern-liga }
        span:nth-child(2) { font-family: no-kern-liga }
      </style>
      <span>kk liga</span><span>kk liga</span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span1, span2 = line.children
    assert span1.width == (1.5 + 1 + 1.5) * 16
    assert span2.width == (2 + 1 + 4) * 16


@assert_no_logs
def test_font_face_descriptors():
    page, = render_pages(
        '''
        <style>
          @font-face {
            src: url(weasyprint.otf);
            font-family: weasyprint;
            font-variant: sub
                          discretionary-ligatures
                          oldstyle-nums
                          slashed-zero;
          }
          span { font-family: weasyprint }
        </style>'''
        '<span>kk</span>'
        '<span>subs</span>'
        '<span>dlig</span>'
        '<span>onum</span>'
        '<span>zero</span>')
    html, = page.children
    body, = html.children
    line, = body.children
    kern, subs, dlig, onum, zero = line.children
    assert kern.width == 1.5 * 16
    assert subs.width == 1.5 * 16
    assert dlig.width == 1.5 * 16
    assert onum.width == 1.5 * 16
    assert zero.width == 1.5 * 16
