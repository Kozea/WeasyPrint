"""
    weasyprint.tests.test_draw.test_acid2
    -------------------------------------

    Check the famous Acid2 test.

"""

import io

import pytest
from PIL import Image
from weasyprint import HTML

from .draw import assert_pixels_equal
from .testing_utils import assert_no_logs, capture_logs, resource_filename


@pytest.mark.xfail
@assert_no_logs
def test_acid2():
    # TODO: fails because of Ghostscript rendering
    def render(filename):
        return HTML(resource_filename(filename)).render()

    with capture_logs():
        # This is a copy of http://www.webstandards.org/files/acid2/test.html
        document = render('acid2-test.html')
        intro_page, test_page = document.pages
        # Ignore the intro page: it is not in the reference
        test_png = document.copy([test_page]).write_png()
        test_pixels = Image.open(io.BytesIO(test_png)).getdata()

    # This is a copy of http://www.webstandards.org/files/acid2/reference.html
    ref_png = render('acid2-reference.html').write_png()
    ref_image = Image.open(io.BytesIO(ref_png))
    ref_pixels = ref_image.getdata()
    width, height = ref_image.size

    assert_pixels_equal(
        'acid2', width, height, test_pixels, ref_pixels, tolerance=2)
