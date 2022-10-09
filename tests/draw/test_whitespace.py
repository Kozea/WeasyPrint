"""Test how white spaces collapse."""

from ..testing_utils import assert_no_logs


@assert_no_logs
def test_whitespace_inline(assert_pixels):
    assert_pixels('''
        RRRR__RRRR____
        RRRR__RRRR____
        ______________
        ______________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {size: 14px 4px}
            body {
              color: red;
              font-family: weasyprint;
              font-size: 2px;
              line-height: 1;
            }
        </style>
        <span>aa </span><span> aa</span>
    ''')


@assert_no_logs
def test_whitespace_nested_inline(assert_pixels):
    assert_pixels('''
        RRRR__RRRR____
        RRRR__RRRR____
        ______________
        ______________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {size: 14px 4px}
            body {
              color: red;
              font-family: weasyprint;
              font-size: 2px;
              line-height: 1;
            }
        </style>
        <span><span>aa </span></span><span><span> aa</span></span>
    ''')


@assert_no_logs
def test_whitespace_inline_space_between(assert_pixels):
    assert_pixels('''
        RRRR__RRRR____
        RRRR__RRRR____
        ______________
        ______________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {size: 14px 4px}
            body {
              color: red;
              font-family: weasyprint;
              font-size: 2px;
              line-height: 1;
            }
        </style>
        <span>aa </span> <span> aa</span>
    ''')


@assert_no_logs
def test_whitespace_float_between(assert_pixels):
    assert_pixels('''
        RRRR__RRRR__BB
        RRRR__RRRR__BB
        ______________
        ______________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {size: 14px 4px}
            body {
              color: red;
              font-family: weasyprint;
              font-size: 2px;
              line-height: 1;
            }
            div {float: right; color: blue}
        </style>
        <span>aa </span><div>a</div><span> aa</span>
    ''')


@assert_no_logs
def test_whitespace_in_float(assert_pixels):
    assert_pixels('''
        RRRRRRRR____BB
        RRRRRRRR____BB
        ______________
        ______________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {size: 14px 4px}
            body {
              color: red;
              font-family: weasyprint;
              font-size: 2px;
              line-height: 1;
            }
            div {
              color: blue;
              float: right;
            }
        </style>
        <span>aa</span><div> a </div><span>aa</span>
    ''')


@assert_no_logs
def test_whitespace_absolute_between(assert_pixels):
    assert_pixels('''
        RRRR__RRRR__BB
        RRRR__RRRR__BB
        ______________
        ______________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {size: 14px 4px}
            body {
              color: red;
              font-family: weasyprint;
              font-size: 2px;
              line-height: 1;
            }
            div {
              color: blue;
              position: absolute;
              right: 0;
              top: 0;
            }
        </style>
        <span>aa </span><div>a</div><span> aa</span>
    ''')


@assert_no_logs
def test_whitespace_in_absolute(assert_pixels):
    assert_pixels('''
        RRRRRRRR____BB
        RRRRRRRR____BB
        ______________
        ______________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {size: 14px 4px}
            body {
              color: red;
              font-family: weasyprint;
              font-size: 2px;
              line-height: 1;
            }
            div {
              color: blue;
              position: absolute;
              right: 0;
              top: 0;
            }
        </style>
        <span>aa</span><div> a </div><span>aa</span>
    ''')


@assert_no_logs
def test_whitespace_running_between(assert_pixels):
    assert_pixels('''
        RRRR__RRRR____
        RRRR__RRRR____
        ______BB______
        ______BB______
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
              size: 14px 4px;
              margin: 0 0 2px;
              @bottom-center {
                content: element(test);
              }
            }
            body {
              color: red;
              font-family: weasyprint;
              font-size: 2px;
              line-height: 1;
            }
            div {
              background: green;
              color: blue;
              position: running(test);
            }
        </style>
        <span>aa </span><div>a</div><span> aa</span>
    ''')


@assert_no_logs
def test_whitespace_in_running(assert_pixels):
    assert_pixels('''
        RRRRRRRR______
        RRRRRRRR______
        ______BB______
        ______BB______
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
              size: 14px 4px;
              margin: 0 0 2px;
              @bottom-center {
                content: element(test);
              }
            }
            body {
              color: red;
              font-family: weasyprint;
              font-size: 2px;
              line-height: 1;
            }
            div {
              background: green;
              color: blue;
              position: running(test);
            }
        </style>
        <span>aa</span><div> a </div><span>aa</span>
    ''')
