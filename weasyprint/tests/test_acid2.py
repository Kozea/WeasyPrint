"""
    weasyprint.tests.test_draw.test_acid2
    -------------------------------------

    Check the famous Acid2 test.

"""

import io

from PIL import Image

from .. import HTML
from .test_draw import assert_pixels_equal
from .testing_utils import assert_no_logs, capture_logs, resource_filename


@assert_no_logs
def test_acid2():
    def render(filename):
        return HTML(resource_filename(filename)).render()

    with capture_logs():
        # This is a copy of http://www.webstandards.org/files/acid2/test.html
        document = render('acid2-test.html')
        intro_page, test_page = document.pages
        # Ignore the intro page: it is not in the reference
        test_png, width, height = document.copy([test_page]).write_png()

    # This is a copy of http://www.webstandards.org/files/acid2/reference.html
    ref_png, ref_width, ref_height = render('acid2-reference.html').write_png()

    assert (width, height) == (ref_width, ref_height)
    assert_pixels_equal(
        'acid2', width, height, Image.open(io.BytesIO(test_png)).getdata(),
        Image.open(io.BytesIO(ref_png)).getdata(), tolerance=2)
