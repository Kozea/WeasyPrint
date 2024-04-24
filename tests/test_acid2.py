"""Check the famous Acid2 test."""

import io

from PIL import Image

from weasyprint import CSS, HTML

from .testing_utils import assert_no_logs, capture_logs, resource_path


@assert_no_logs
def test_acid2(assert_pixels_equal):
    # Reduce image size and avoid Ghostscript rounding problems
    stylesheets = (CSS(string='@page { size: 500px 800px }'),)

    def render(filename):
        return HTML(resource_path(filename)).render(stylesheets=stylesheets)

    with capture_logs():
        # This is a copy of https://www.webstandards.org/files/acid2/test.html
        document = render('acid2-test.html')
        intro_page, test_page = document.pages
        # Ignore the intro page: it is not in the reference
        test_png = document.copy([test_page]).write_png()
        test_pixels = Image.open(io.BytesIO(test_png)).getdata()

    # This is a copy of https://www.webstandards.org/files/acid2/reference.html
    ref_png = render('acid2-reference.html').write_png()
    ref_image = Image.open(io.BytesIO(ref_png))
    ref_pixels = ref_image.getdata()
    width, height = ref_image.size

    assert_pixels_equal(width, height, test_pixels, ref_pixels, tolerance=2)
