"""
    weasyprint.tests.test_draw.test_acid2
    -------------------------------------

    Check the famous Acid2 test.

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from .. import HTML
from .test_draw import assert_pixels_equal, image_to_pixels
from .testing_utils import (
    assert_no_logs, capture_logs, requires, resource_filename)


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_acid2():
    def render(filename):
        return HTML(resource_filename(filename)).render(enable_hinting=True)

    with capture_logs():
        # This is a copy of http://www.webstandards.org/files/acid2/test.html
        document = render('acid2-test.html')
        intro_page, test_page = document.pages
        # Ignore the intro page: it is not in the reference
        test_image, width, height = document.copy(
            [test_page]).write_image_surface()

    # This is a copy of http://www.webstandards.org/files/acid2/reference.html
    ref_image, ref_width, ref_height = render(
        'acid2-reference.html').write_image_surface()

    assert (width, height) == (ref_width, ref_height)
    assert_pixels_equal(
        'acid2', width, height, image_to_pixels(test_image, width, height),
        image_to_pixels(ref_image, width, height), tolerance=2)
