"""Helpers for tests."""

import contextlib
import functools
import logging
import sys
from pathlib import Path

from weasyprint import CSS, DEFAULT_OPTIONS, HTML, images
from weasyprint.css import get_all_computed_styles
from weasyprint.css.counters import CounterStyle
from weasyprint.css.targets import TargetCollector
from weasyprint.formatting_structure import boxes, build
from weasyprint.html import HTML5_UA_STYLESHEET
from weasyprint.logger import LOGGER
from weasyprint.urls import path2url

# Lists of fonts with many variants (including condensed)
if sys.platform.startswith('win'):  # pragma: no cover
    SANS_FONTS = 'DejaVu Sans, Arial Nova, Arial, sans'
    MONO_FONTS = 'Courier New, Courier, monospace'
else:  # pragma: no cover
    SANS_FONTS = 'DejaVu Sans, sans'
    MONO_FONTS = 'DejaVu Sans Mono, monospace'

TEST_UA_STYLESHEET = CSS(
    Path(__file__).parent.parent / 'weasyprint' / 'css' / 'tests_ua.css')

PROPER_CHILDREN = {
    # Children can be of *any* type in *one* of the lists.
    boxes.BlockContainerBox: ((boxes.BlockLevelBox,), (boxes.LineBox,)),
    boxes.LineBox: ((boxes.InlineLevelBox,),),
    boxes.InlineBox: ((boxes.InlineLevelBox,),),
    boxes.TableBox: ((
        boxes.TableCaptionBox, boxes.TableColumnGroupBox, boxes.TableColumnBox,
        boxes.TableRowGroupBox, boxes.TableRowBox),),
    boxes.InlineTableBox: ((
        boxes.TableCaptionBox, boxes.TableColumnGroupBox, boxes.TableColumnBox,
        boxes.TableRowGroupBox, boxes.TableRowBox),),
    boxes.TableColumnGroupBox: ((boxes.TableColumnBox,),),
    boxes.TableRowGroupBox: ((boxes.TableRowBox,),),
    boxes.TableRowBox: ((boxes.TableCellBox,),),
}


class FakeHTML(HTML):
    """Like weasyprint.HTML, but with a lighter UA stylesheet."""
    def __init__(self, *args, force_uncompressed_pdf=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._force_uncompressed_pdf = force_uncompressed_pdf

    def _ua_stylesheets(self, forms=False):
        return [
            TEST_UA_STYLESHEET if stylesheet == HTML5_UA_STYLESHEET
            else stylesheet for stylesheet in super()._ua_stylesheets(forms)]

    def write_pdf(self, target=None, zoom=1, finisher=None, **options):
        # Override function to force the generation of uncompressed PDFs
        if self._force_uncompressed_pdf:
            options['uncompressed_pdf'] = True
        return super().write_pdf(target, zoom, finisher, **options)


def resource_path(name):
    """Return the absolute path of the resource called ``name``."""
    return Path(__file__).parent / 'resources' / name


# Dummy filename, but in the right directory.
BASE_URL = path2url(resource_path('<test>'))


class CallbackHandler(logging.Handler):
    """A logging handler that calls a function for every message."""
    def __init__(self, callback):
        logging.Handler.__init__(self)
        self.emit = callback


@contextlib.contextmanager
def capture_logs():
    """Return a context manager that captures all logged messages."""
    logger = LOGGER
    messages = []

    def emit(record):
        if record.name == 'weasyprint.progress':
            return
        messages.append(f'{record.levelname.upper()}: {record.getMessage()}')

    previous_handlers = logger.handlers
    previous_level = logger.level
    logger.handlers = []
    logger.addHandler(CallbackHandler(emit))
    logger.setLevel(logging.DEBUG)
    try:
        yield messages
    finally:
        logger.handlers = previous_handlers
        logger.level = previous_level


def assert_no_logs(function):
    """Decorator that asserts that nothing is logged in a function."""
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        with capture_logs() as logs:
            try:
                function(*args, **kwargs)
            except Exception:  # pragma: no cover
                if logs:
                    print(f'{len(logs)} errors logged:', file=sys.stderr)
                    for message in logs:
                        print(message, file=sys.stderr)
                raise
            else:
                if logs:  # pragma: no cover
                    for message in logs:
                        print(message, file=sys.stderr)
                    raise AssertionError(f'{len(logs)} errors logged')
    return wrapper


def serialize(box_list):
    """Transform a box list into a structure easier to compare for testing."""
    return [(
        box.element_tag,
        type(box).__name__[:-3],
        # All concrete boxes are either text, replaced, column or parent.
        (box.text if isinstance(box, boxes.TextBox)
            else '<replaced>' if isinstance(box, boxes.ReplacedBox)
            else serialize(
                getattr(box, 'column_groups', ()) + tuple(box.children))))
            for box in box_list]


def tree_position(box_list, matcher):
    """Return a list identifying the first matching box's tree position.

    Given a list of Boxes, this function returns a list containing the first
    (depth-first) Box that the matcher function identifies. This list can then
    be compared to another similarly-obtained list to assert that one Box is in
    the document tree before or after another.

    box_list: a list of Box objects, possibly PageBoxes
    matcher: a function that takes a Box and returns truthy when it matches

    """
    for i, box in enumerate(box_list):
        if matcher(box):
            return [i]
        elif hasattr(box, 'children'):
            position = tree_position(box.children, matcher)
            if position:
                return [i, *position]


def _parse_base(html_content, base_url=BASE_URL):
    document = FakeHTML(string=html_content, base_url=base_url)
    counter_style = CounterStyle()
    style_for = get_all_computed_styles(document, counter_style=counter_style)
    get_image_from_uri = functools.partial(
        images.get_image_from_uri, cache={}, url_fetcher=document.url_fetcher,
        options=DEFAULT_OPTIONS)
    target_collector = TargetCollector()
    footnotes = []
    return (
        document.etree_element, style_for, get_image_from_uri, base_url,
        target_collector, counter_style, footnotes)


def parse(html_content):
    """Parse some HTML, apply stylesheets and transform to boxes."""
    box, = build.element_to_box(*_parse_base(html_content))
    return box


def parse_all(html_content, base_url=BASE_URL):
    """Like parse() but also run all corrections on boxes."""
    box = build.build_formatting_structure(*_parse_base(
        html_content, base_url))
    _sanity_checks(box)
    return box


def render_pages(html_content):
    """Lay out a document and return a list of PageBox objects."""
    return [
        page._page_box for page in
        FakeHTML(string=html_content, base_url=BASE_URL).render().pages]


def assert_tree(box, expected):
    """Check the box tree equality.

    The obtained result is prettified in the message in case of failure.

    box: a Box object, starting with <html> and <body> blocks.
    expected: a list of serialized <body> children as returned by to_lists().

    """
    assert box.element_tag == 'html'
    assert isinstance(box, boxes.BlockBox)
    assert len(box.children) == 1

    box = box.children[0]
    assert isinstance(box, boxes.BlockBox)
    assert box.element_tag == 'body'

    assert serialize(box.children) == expected


def _sanity_checks(box):
    """Check that the rules regarding boxes are met.

    This is not required and only helps debugging.

    - A block container can contain either only block-level boxes or
      only line boxes;
    - Line boxes and inline boxes can only contain inline-level boxes.

    """
    if not isinstance(box, boxes.ParentBox):
        return

    acceptable_types_lists = None  # raises when iterated
    for class_ in type(box).mro():  # pragma: no cover
        if class_ in PROPER_CHILDREN:
            acceptable_types_lists = PROPER_CHILDREN[class_]
            break

    assert any(
        all(isinstance(child, acceptable_types) or
            not child.is_in_normal_flow()
            for child in box.children)
        for acceptable_types in acceptable_types_lists
    ), (box, box.children)

    for child in box.children:
        _sanity_checks(child)
