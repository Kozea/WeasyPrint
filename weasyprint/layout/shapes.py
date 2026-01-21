"""CSS Shapes support for shape-outside property.

This module provides shape boundary classes for computing exclusion areas
around floated elements. Each boundary class implements the same interface
for querying shape bounds at specific Y coordinates.
"""

import math
from abc import ABC, abstractmethod

from ..css.units import LENGTHS_TO_PIXELS
from ..logger import LOGGER
from ..urls import URLFetchingError, fetch


class ShapeBoundary(ABC):
    """Abstract base class for shape-outside boundaries.

    Shape boundaries compute the horizontal exclusion range at any given
    Y coordinate within the shape's vertical extent.
    """

    @abstractmethod
    def get_bounds_at_y(self, y):
        """Get horizontal bounds of the shape at a specific Y coordinate.

        Args:
            y: The Y coordinate to query.

        Returns:
            tuple: (left_bound, right_bound) in absolute coordinates,
                   or None if the shape doesn't intersect at this Y.
        """
        pass

    @abstractmethod
    def get_vertical_extent(self):
        """Get the vertical range of the shape.

        Returns:
            tuple: (min_y, max_y) of the shape's vertical extent.
        """
        pass


class BoxBoundary(ShapeBoundary):
    """Rectangular boundary based on CSS box model.

    This boundary returns constant horizontal bounds regardless of Y position.
    For box-based shapes, the horizontal bounds don't vary with Y, so we always
    return the same bounds. The margin box is used for collision detection.
    """

    def __init__(self, box, box_type='margin-box'):
        """Initialize a box boundary.

        Args:
            box: The float box to compute bounds from.
            box_type: One of 'margin-box', 'border-box', 'padding-box',
                'content-box'.
        """
        self.box = box
        self.box_type = box_type
        self._compute_bounds()

    def _compute_bounds(self):
        """Precompute the box bounds.

        Computes horizontal bounds based on box_type for shape-outside,
        and vertical extent based on margin box for collision detection.
        """
        box = self.box
        # Horizontal bounds depend on the box_type (shape-outside value)
        if self.box_type == 'content-box':
            self.left = box.content_box_x()
            self.right = self.left + box.width
        elif self.box_type == 'padding-box':
            self.left = box.padding_box_x()
            self.right = self.left + box.padding_width()
        elif self.box_type == 'border-box':
            self.left = box.border_box_x()
            self.right = self.left + box.border_width()
        else:  # margin-box (default)
            self.left = box.position_x
            self.right = self.left + box.margin_width()

        # Vertical extent always uses margin box for collision detection
        # This matches the original behavior where collision detection
        # uses margin_height() but shape bounds use shape-outside value
        self.top = box.position_y
        self.bottom = self.top + box.margin_height()

    def get_bounds_at_y(self, y):
        """Get horizontal bounds at the given Y coordinate.

        For box-based shapes, horizontal bounds are constant regardless of Y.
        Since the collision detection in avoid_collisions() already checks
        for vertical overlap, we always return the bounds here. The collision
        detection handles cases where the shape overlaps with the box even if
        the query Y is outside the shape's vertical extent.
        """
        # For rectangular shapes, bounds are constant - always return them
        # The collision detection already verified there's vertical overlap
        return (self.left, self.right)

    def get_vertical_extent(self):
        """Get the vertical extent of the box (margin box)."""
        return (self.top, self.bottom)


class CircleBoundary(ShapeBoundary):
    """Circular boundary for circle() shape function."""

    def __init__(self, cx, cy, radius):
        """Initialize circle boundary with absolute coordinates.

        Args:
            cx: Center X coordinate (absolute)
            cy: Center Y coordinate (absolute)
            radius: Circle radius (absolute)
        """
        self.cx = cx
        self.cy = cy
        self.radius = radius

    def get_bounds_at_y(self, y):
        """Get horizontal bounds at Y using circle equation."""
        # Degenerate circle with zero/negative radius has no exclusion area
        if self.radius <= 0:
            return None
        dy = y - self.cy
        if abs(dy) > self.radius:
            return None  # Y is outside circle
        # Circle equation: (x-cx)^2 + (y-cy)^2 = r^2
        # Solve for x: x = cx +/- sqrt(r^2 - (y-cy)^2)
        dx = math.sqrt(self.radius**2 - dy**2)
        return (self.cx - dx, self.cx + dx)

    def get_vertical_extent(self):
        return (self.cy - self.radius, self.cy + self.radius)


class EllipseBoundary(ShapeBoundary):
    """Elliptical boundary for ellipse() shape function."""

    def __init__(self, cx, cy, rx, ry):
        """Initialize ellipse boundary with absolute coordinates.

        Args:
            cx: Center X coordinate (absolute)
            cy: Center Y coordinate (absolute)
            rx: Horizontal radius (absolute)
            ry: Vertical radius (absolute)
        """
        self.cx = cx
        self.cy = cy
        self.rx = rx  # horizontal radius
        self.ry = ry  # vertical radius

    def get_bounds_at_y(self, y):
        """Get horizontal bounds at Y using ellipse equation."""
        # Degenerate ellipse with zero/negative radii has no exclusion area
        if self.rx <= 0 or self.ry <= 0:
            return None
        dy = y - self.cy
        if abs(dy) > self.ry:
            return None
        # Ellipse equation: (x-cx)^2/rx^2 + (y-cy)^2/ry^2 = 1
        # Solve for x: x = cx +/- rx * sqrt(1 - (y-cy)^2/ry^2)
        ratio = 1 - (dy**2 / self.ry**2)
        if ratio < 0:
            return None
        dx = self.rx * math.sqrt(ratio)
        return (self.cx - dx, self.cx + dx)

    def get_vertical_extent(self):
        return (self.cy - self.ry, self.cy + self.ry)


class PolygonBoundary(ShapeBoundary):
    """Polygon boundary using scanline intersection."""

    def __init__(self, points, fill_rule='nonzero'):
        """Initialize with list of absolute (x, y) coordinate tuples.

        Args:
            points: List of (x, y) tuples in absolute coordinates
            fill_rule: 'nonzero' or 'evenodd' (currently only affects
                       future enhancements for complex polygons)
        """
        self.points = points
        self.fill_rule = fill_rule
        # A valid polygon needs at least 3 points to form a closed shape
        self.is_degenerate = len(points) < 3
        # Precompute vertical extent
        if points and not self.is_degenerate:
            ys = [p[1] for p in points]
            self.min_y = min(ys)
            self.max_y = max(ys)
        else:
            self.min_y = 0
            self.max_y = 0

    def get_bounds_at_y(self, y):
        """Get horizontal bounds at Y using scanline intersection."""
        # Degenerate polygon with < 3 points has no exclusion area
        if self.is_degenerate:
            return None

        if y < self.min_y or y > self.max_y:
            return None

        if not self.points:
            return None

        # Scanline intersection algorithm
        intersections = []
        n = len(self.points)

        for i in range(n):
            x1, y1 = self.points[i]
            x2, y2 = self.points[(i + 1) % n]

            # Skip horizontal edges
            if y1 == y2:
                continue

            # Check if scanline intersects this edge
            if not (min(y1, y2) <= y <= max(y1, y2)):
                continue

            # Calculate x intersection using linear interpolation
            t = (y - y1) / (y2 - y1)
            x = x1 + t * (x2 - x1)
            intersections.append(x)

        if len(intersections) < 2:
            return None

        intersections.sort()
        return (intersections[0], intersections[-1])

    def get_vertical_extent(self):
        return (self.min_y, self.max_y)


class InsetBoundary(ShapeBoundary):
    """Inset rectangular boundary with optional rounded corners.

    The inset() function creates a rectangular shape that is inset from
    the reference box edges by the specified amounts.
    """

    def __init__(self, left, top, right, bottom, border_radius=None):
        """Initialize inset boundary with absolute coordinates.

        Args:
            left: Left edge X coordinate (absolute)
            top: Top edge Y coordinate (absolute)
            right: Right edge X coordinate (absolute)
            bottom: Bottom edge Y coordinate (absolute)
            border_radius: Optional tuple of 4 corner radii
        """
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.border_radius = border_radius

    def get_bounds_at_y(self, y):
        """Get horizontal bounds at Y, accounting for rounded corners."""
        if y < self.top or y > self.bottom:
            return None

        left = self.left
        right = self.right

        # Handle rounded corners if present
        if self.border_radius:
            tl_r, tr_r, br_r, bl_r = self.border_radius

            # Top-left corner adjustment
            if tl_r > 0 and y < self.top + tl_r:
                dy = y - self.top
                # Circle equation: adjust left bound
                # Use max(0, ...) to guard against floating-point precision issues
                if dy < tl_r:
                    sqrt_arg = max(0, tl_r**2 - (tl_r - dy)**2)
                    dx = tl_r - math.sqrt(sqrt_arg)
                    left = max(left, self.left + dx)

            # Top-right corner adjustment
            if tr_r > 0 and y < self.top + tr_r:
                dy = y - self.top
                if dy < tr_r:
                    sqrt_arg = max(0, tr_r**2 - (tr_r - dy)**2)
                    dx = tr_r - math.sqrt(sqrt_arg)
                    right = min(right, self.right - dx)

            # Bottom-left corner adjustment
            if bl_r > 0 and y > self.bottom - bl_r:
                dy = self.bottom - y
                if dy < bl_r:
                    sqrt_arg = max(0, bl_r**2 - (bl_r - dy)**2)
                    dx = bl_r - math.sqrt(sqrt_arg)
                    left = max(left, self.left + dx)

            # Bottom-right corner adjustment
            if br_r > 0 and y > self.bottom - br_r:
                dy = self.bottom - y
                if dy < br_r:
                    sqrt_arg = max(0, br_r**2 - (br_r - dy)**2)
                    dx = br_r - math.sqrt(sqrt_arg)
                    right = min(right, self.right - dx)

        return (left, right)

    def get_vertical_extent(self):
        return (self.top, self.bottom)


class MarginedBoundary(ShapeBoundary):
    """Wrapper that expands an inner boundary by a margin amount.

    This class wraps another ShapeBoundary and expands its bounds
    outward by the specified margin amount.
    """

    def __init__(self, inner_boundary, margin):
        """Initialize margined boundary.

        Args:
            inner_boundary: The inner ShapeBoundary to expand
            margin: The margin amount to expand by (in pixels)
        """
        self.inner = inner_boundary
        self.margin = margin

    def get_bounds_at_y(self, y):
        """Get horizontal bounds at Y, expanded by margin.

        For non-circular shapes, this is a simplified implementation
        that expands horizontal bounds and checks vertical extent.
        """
        inner_extent = self.inner.get_vertical_extent()
        inner_top, inner_bottom = inner_extent

        # Check if Y is within the expanded vertical range
        if y < inner_top - self.margin or y > inner_bottom + self.margin:
            return None

        # Get inner bounds at this Y (or closest valid Y)
        inner_bounds = self.inner.get_bounds_at_y(y)

        if inner_bounds is not None:
            # Simply expand the bounds by margin
            left, right = inner_bounds
            return (left - self.margin, right + self.margin)

        # Y is in the margin zone above or below the inner shape
        # For shapes like circles, we need to compute the expanded bounds
        if y < inner_top:
            # Above the inner shape - check at inner_top
            inner_bounds = self.inner.get_bounds_at_y(inner_top)
            if inner_bounds:
                left, right = inner_bounds
                # Expand based on circular expansion at the margin
                dy = inner_top - y
                if dy <= self.margin:
                    # Compute horizontal expansion for circular margin
                    dx = math.sqrt(self.margin**2 - dy**2)
                    center = (left + right) / 2
                    half_width = (right - left) / 2 + dx
                    return (center - half_width, center + half_width)
        elif y > inner_bottom:
            # Below the inner shape - check at inner_bottom
            inner_bounds = self.inner.get_bounds_at_y(inner_bottom)
            if inner_bounds:
                left, right = inner_bounds
                dy = y - inner_bottom
                if dy <= self.margin:
                    dx = math.sqrt(self.margin**2 - dy**2)
                    center = (left + right) / 2
                    half_width = (right - left) / 2 + dx
                    return (center - half_width, center + half_width)

        return None

    def get_vertical_extent(self):
        """Get the vertical extent expanded by margin."""
        inner_extent = self.inner.get_vertical_extent()
        return (inner_extent[0] - self.margin, inner_extent[1] + self.margin)


class ImageBoundary(ShapeBoundary):
    """Image-based boundary using alpha channel extraction.

    This class extracts the shape from an image's alpha channel.
    Pixels with alpha values greater than the threshold are considered
    inside the shape.
    """

    def __init__(self, image_data, threshold, ref_x, ref_y, ref_w, ref_h):
        """Initialize image boundary.

        Args:
            image_data: PIL Image or image bytes
            threshold: Alpha threshold (0.0-1.0) for shape extraction
            ref_x, ref_y: Reference box position (absolute)
            ref_w, ref_h: Reference box dimensions
        """
        self.ref_x = ref_x
        self.ref_y = ref_y
        self.ref_w = ref_w
        self.ref_h = ref_h
        self.threshold = threshold
        self.alpha_data = None
        self.img_width = 0
        self.img_height = 0

        # Extract alpha channel from image
        self._extract_alpha(image_data)

        # Cache for scanline bounds
        self._bounds_cache = {}

    def _extract_alpha(self, image_data):
        """Extract alpha channel from image data."""
        try:
            from PIL import Image
            import io

            # Handle different image data types
            if isinstance(image_data, Image.Image):
                img = image_data
            elif isinstance(image_data, bytes):
                img = Image.open(io.BytesIO(image_data))
            else:
                # Fallback - no valid image
                return

            # Convert to RGBA if needed
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            self.img_width = img.width
            self.img_height = img.height

            # Extract alpha channel as a 2D array using img.load() for faster access
            # img.load() returns a PixelAccess object that is much faster than getpixel()
            pixels = img.load()
            self.alpha_data = []
            for y in range(img.height):
                row = []
                for x in range(img.width):
                    # Get alpha value (0-255), normalize to 0-1
                    pixel = pixels[x, y]
                    alpha = pixel[3] / 255.0 if len(pixel) > 3 else 1.0
                    row.append(alpha)
                self.alpha_data.append(row)

        except Exception as exc:
            # If image loading fails, alpha_data remains None
            LOGGER.warning('Failed to extract alpha channel from shape image: %s', exc)

    def get_bounds_at_y(self, y):
        """Get horizontal bounds at Y by scanning alpha channel."""
        if self.alpha_data is None or self.img_height == 0:
            return None

        # Check cache
        if y in self._bounds_cache:
            return self._bounds_cache[y]

        # Map y coordinate to image row
        rel_y = y - self.ref_y
        if rel_y < 0 or rel_y >= self.ref_h:
            return None

        # Scale to image coordinates
        img_y = int((rel_y / self.ref_h) * self.img_height)
        img_y = max(0, min(self.img_height - 1, img_y))

        row = self.alpha_data[img_y]

        # Scan for left and right bounds
        left_bound = None
        right_bound = None

        for x, alpha in enumerate(row):
            if alpha > self.threshold:
                # Map image x to reference box coordinates
                ref_x = self.ref_x + (x / self.img_width) * self.ref_w
                if left_bound is None:
                    left_bound = ref_x
                right_bound = ref_x

        if left_bound is None:
            # No pixels above threshold at this y
            result = None
        else:
            # Extend right bound to include the full pixel width
            pixel_width = self.ref_w / self.img_width
            result = (left_bound, right_bound + pixel_width)

        self._bounds_cache[y] = result
        return result

    def get_vertical_extent(self):
        """Get the vertical extent of the shape."""
        if self.alpha_data is None:
            return (self.ref_y, self.ref_y + self.ref_h)

        # Find first and last rows with pixels above threshold
        min_y = None
        max_y = None

        for img_y, row in enumerate(self.alpha_data):
            if any(alpha > self.threshold for alpha in row):
                ref_y = self.ref_y + (img_y / self.img_height) * self.ref_h
                if min_y is None:
                    min_y = ref_y
                max_y = ref_y

        if min_y is None:
            return (self.ref_y, self.ref_y + self.ref_h)

        # Extend max_y to include full pixel height
        pixel_height = self.ref_h / self.img_height
        return (min_y, max_y + pixel_height)


def create_shape_boundary(box, context=None):
    """Create a shape boundary for a floated box.

    Args:
        box: The float box with shape_outside style.
        context: The layout context (provides access to url_fetcher for images).

    Returns:
        ShapeBoundary: A boundary object for computing shape exclusions.
    """
    shape_outside = box.style['shape_outside']
    shape_margin = box.style['shape_margin']

    # Determine the reference box type (default is margin-box)
    ref_box_type = 'margin-box'

    # Handle shape_with_box tuple: ('shape_with_box', shape, ref_box)
    if isinstance(shape_outside, tuple) and shape_outside[0] == 'shape_with_box':
        _, shape_outside, ref_box_type = shape_outside

    # Create the base boundary
    boundary = _create_base_boundary(box, shape_outside, ref_box_type, context)

    # Apply shape-margin if specified (check value > 0)
    if hasattr(shape_margin, 'value') and shape_margin.value > 0:
        margin_value = resolve_position_value(shape_margin, box.margin_width())
        boundary = MarginedBoundary(boundary, margin_value)

    return boundary


def _create_base_boundary(box, shape_outside, ref_box_type='margin-box', context=None):
    """Create the base shape boundary without margin.

    Args:
        box: The float box with shape_outside style.
        shape_outside: The shape specification (string or tuple).
        ref_box_type: The reference box type for shape functions.
        context: The layout context (provides access to url_fetcher for images).

    Returns:
        ShapeBoundary: A boundary object for computing shape exclusions.
    """
    # String keywords
    if isinstance(shape_outside, str):
        box_type = None
        if shape_outside in ('none', 'margin-box'):
            box_type = 'margin-box'
        elif shape_outside == 'border-box':
            box_type = 'border-box'
        elif shape_outside == 'padding-box':
            box_type = 'padding-box'
        elif shape_outside == 'content-box':
            box_type = 'content-box'

        if box_type:
            # Check if box has border-radius - if so, create InsetBoundary with corners
            border_radii = _get_border_radii(box)
            if border_radii and any(r > 0 for r in border_radii):
                # Create inset boundary with 0 inset and the border-radius values
                ref_x, ref_y, ref_w, ref_h = get_reference_box(box, box_type)
                return InsetBoundary(ref_x, ref_y, ref_x + ref_w, ref_y + ref_h, border_radii)
            return BoxBoundary(box, box_type)

    # Shape functions (tuples)
    elif isinstance(shape_outside, tuple):
        shape_type = shape_outside[0]

        if shape_type == 'circle':
            cx, cy, radius = resolve_circle_params(shape_outside, box, ref_box_type)
            return CircleBoundary(cx, cy, radius)

        elif shape_type == 'ellipse':
            cx, cy, rx, ry = resolve_ellipse_params(shape_outside, box, ref_box_type)
            return EllipseBoundary(cx, cy, rx, ry)

        elif shape_type == 'polygon':
            points = resolve_polygon_params(shape_outside, box, ref_box_type)
            fill_rule = shape_outside[1]
            return PolygonBoundary(points, fill_rule)

        elif shape_type == 'inset':
            return resolve_inset_boundary(shape_outside, box, ref_box_type)

        elif shape_type == 'image':
            # Image-based shape: ('image', url_info, ref_box_type)
            url_info = shape_outside[1]
            image_ref_box = shape_outside[2] if len(shape_outside) > 2 else 'margin-box'
            return _create_image_boundary(box, url_info, image_ref_box, context)

    # Fallback
    return BoxBoundary(box, 'margin-box')


def _create_image_boundary(box, url_info, ref_box_type, context=None):
    """Create an ImageBoundary from a URL.

    Args:
        box: The float box
        url_info: URL info tuple from CSS parsing (e.g., ('external', url))
        ref_box_type: Reference box type for the image
        context: The layout context (provides access to url_fetcher for images)

    Returns:
        ImageBoundary or BoxBoundary fallback
    """
    # Get reference box dimensions
    ref_x, ref_y, ref_w, ref_h = get_reference_box(box, ref_box_type)

    # Get threshold from style
    threshold = box.style.get('shape_image_threshold', 0.0)
    if threshold is None:
        threshold = 0.0

    # Try to load the image using WeasyPrint's URL fetcher
    try:
        # URL info can be ('external', url) or ('internal', data)
        if isinstance(url_info, tuple):
            url_type, url_data = url_info
            if url_type == 'external':
                # Load external image using WeasyPrint's URL fetcher
                if context is not None:
                    # Get the url_fetcher from the context's get_image_from_uri partial
                    url_fetcher = context.get_image_from_uri.keywords.get('url_fetcher')
                    if url_fetcher is not None:
                        with fetch(url_fetcher, url_data) as response:
                            image_data = response.read()
                        return ImageBoundary(
                            image_data, threshold, ref_x, ref_y, ref_w, ref_h)

                # Fallback: if no context or url_fetcher, use URLFetcher directly
                from ..urls import URLFetcher
                url_fetcher = URLFetcher()
                with fetch(url_fetcher, url_data) as response:
                    image_data = response.read()
                return ImageBoundary(image_data, threshold, ref_x, ref_y, ref_w, ref_h)

            elif url_type == 'internal':
                # Internal data (already loaded)
                return ImageBoundary(url_data, threshold, ref_x, ref_y, ref_w, ref_h)

        elif isinstance(url_info, str):
            # Direct file path or URL string
            # Use WeasyPrint's URL fetcher for proper handling
            if context is not None:
                url_fetcher = context.get_image_from_uri.keywords.get('url_fetcher')
                if url_fetcher is not None:
                    with fetch(url_fetcher, url_info) as response:
                        image_data = response.read()
                    return ImageBoundary(
                        image_data, threshold, ref_x, ref_y, ref_w, ref_h)

            # Fallback: use URLFetcher directly
            from ..urls import URLFetcher
            url_fetcher = URLFetcher()
            with fetch(url_fetcher, url_info) as response:
                image_data = response.read()
            return ImageBoundary(image_data, threshold, ref_x, ref_y, ref_w, ref_h)

    except URLFetchingError as exc:
        LOGGER.warning('Failed to load shape image at %r: %s', url_info, exc)
    except Exception as exc:
        LOGGER.warning('Failed to load shape image at %r: %s', url_info, exc)

    return BoxBoundary(box, ref_box_type)


# ---------------------------------------------------------------------------
# Parameter Resolution Functions
# ---------------------------------------------------------------------------

def _get_border_radii(box):
    """Extract border-radius values from a box.

    Returns tuple of (top-left, top-right, bottom-right, bottom-left) radii
    in pixels, or None if no border-radius.
    """
    # Border radius values are in box.style as computed values (tuples of Dimensions)
    # They need to be resolved to pixels similar to resolve_radii_percentages
    style = box.style
    border_width = box.border_width()
    border_height = box.border_height()

    def resolve_radius(computed):
        """Resolve a computed radius tuple (rx, ry) to pixel values."""
        if computed is None or computed == (0, 0):
            return (0, 0)
        rx, ry = computed
        # Check for zero values
        if hasattr(rx, 'value') and hasattr(ry, 'value'):
            if rx.value == 0 or ry.value == 0:
                return (0, 0)
        # Resolve percentages or extract pixel values
        if hasattr(rx, 'unit'):
            if rx.unit == '%':
                rx_px = border_width * rx.value / 100
            elif rx.unit and rx.unit.lower() == 'px':
                rx_px = rx.value
            elif rx.unit in LENGTHS_TO_PIXELS:
                rx_px = rx.value * LENGTHS_TO_PIXELS[rx.unit]
            else:
                rx_px = rx.value if rx.value else 0
        else:
            rx_px = float(rx) if rx else 0
        if hasattr(ry, 'unit'):
            if ry.unit == '%':
                ry_px = border_height * ry.value / 100
            elif ry.unit and ry.unit.lower() == 'px':
                ry_px = ry.value
            elif ry.unit in LENGTHS_TO_PIXELS:
                ry_px = ry.value * LENGTHS_TO_PIXELS[ry.unit]
            else:
                ry_px = ry.value if ry.value else 0
        else:
            ry_px = float(ry) if ry else 0
        return (rx_px, ry_px)

    tl = resolve_radius(style['border_top_left_radius'])
    tr = resolve_radius(style['border_top_right_radius'])
    br = resolve_radius(style['border_bottom_right_radius'])
    bl = resolve_radius(style['border_bottom_left_radius'])

    # For shape-outside, use the horizontal radius (first value)
    # since that's what affects horizontal text wrapping
    radii = (tl[0], tr[0], br[0], bl[0])

    if all(r == 0 for r in radii):
        return None
    return radii


def get_reference_box(box, ref_box_type='margin-box'):
    """Get the reference box coordinates for a given box type.

    Args:
        box: The float box
        ref_box_type: One of 'margin-box', 'border-box', 'padding-box', 'content-box'

    Returns:
        Tuple (ref_x, ref_y, ref_w, ref_h) - position and dimensions
    """
    if ref_box_type == 'content-box':
        ref_x = box.content_box_x()
        ref_y = box.content_box_y()
        ref_w = box.width
        ref_h = box.height
    elif ref_box_type == 'padding-box':
        ref_x = box.padding_box_x()
        ref_y = box.padding_box_y()
        ref_w = box.padding_width()
        ref_h = box.padding_height()
    elif ref_box_type == 'border-box':
        ref_x = box.border_box_x()
        ref_y = box.border_box_y()
        ref_w = box.border_width()
        ref_h = box.border_height()
    else:  # margin-box (default)
        ref_x = box.position_x
        ref_y = box.position_y
        ref_w = box.margin_width()
        ref_h = box.margin_height()

    return (ref_x, ref_y, ref_w, ref_h)


def resolve_circle_params(shape_value, box, ref_box_type='margin-box'):
    """Resolve circle() parameters to absolute values.

    Args:
        shape_value: Tuple ('circle', radius, position)
        box: The float box for resolving percentages
        ref_box_type: The reference box type for resolving percentages

    Returns:
        Tuple (cx, cy, radius) in absolute coordinates
    """
    _, radius_spec, position = shape_value

    # Get reference box dimensions
    ref_x, ref_y, ref_w, ref_h = get_reference_box(box, ref_box_type)

    # Resolve position (cx, cy)
    cx = resolve_position_value(position[0], ref_w) + ref_x
    cy = resolve_position_value(position[1], ref_h) + ref_y

    # Resolve radius
    radius = resolve_shape_radius(
        radius_spec, ref_w, ref_h, cx, cy, ref_x, ref_y)

    return (cx, cy, radius)


def resolve_ellipse_params(shape_value, box, ref_box_type='margin-box'):
    """Resolve ellipse() parameters to absolute values.

    Args:
        shape_value: Tuple ('ellipse', rx, ry, position)
        box: The float box for resolving percentages
        ref_box_type: The reference box type for resolving percentages

    Returns:
        Tuple (cx, cy, rx, ry) in absolute coordinates
    """
    _, rx_spec, ry_spec, position = shape_value

    # Get reference box dimensions
    ref_x, ref_y, ref_w, ref_h = get_reference_box(box, ref_box_type)

    # Resolve position (cx, cy)
    cx = resolve_position_value(position[0], ref_w) + ref_x
    cy = resolve_position_value(position[1], ref_h) + ref_y

    # Resolve radii
    rx = resolve_ellipse_radius(
        rx_spec, ref_w, ref_h, cx, cy, ref_x, ref_y, is_horizontal=True)
    ry = resolve_ellipse_radius(
        ry_spec, ref_w, ref_h, cx, cy, ref_x, ref_y, is_horizontal=False)

    return (cx, cy, rx, ry)


def resolve_polygon_params(shape_value, box, ref_box_type='margin-box'):
    """Resolve polygon() parameters to absolute values.

    Args:
        shape_value: Tuple ('polygon', fill_rule, ((x1,y1), (x2,y2), ...))
        box: The float box for resolving percentages
        ref_box_type: The reference box type for resolving percentages

    Returns:
        List of (x, y) tuples in absolute coordinates
    """
    _, fill_rule, point_specs = shape_value

    # Get reference box dimensions
    ref_x, ref_y, ref_w, ref_h = get_reference_box(box, ref_box_type)

    points = []
    for x_spec, y_spec in point_specs:
        x = resolve_position_value(x_spec, ref_w) + ref_x
        y = resolve_position_value(y_spec, ref_h) + ref_y
        points.append((x, y))

    return points


def resolve_inset_boundary(shape_value, box, ref_box_type='margin-box'):
    """Resolve inset() parameters and create an InsetBoundary.

    Args:
        shape_value: Tuple ('inset', (top, right, bottom, left), border_radius)
        box: The float box for resolving percentages
        ref_box_type: The reference box type for resolving percentages

    Returns:
        InsetBoundary with absolute coordinates
    """
    _, offsets, border_radius = shape_value

    # Get reference box dimensions
    ref_x, ref_y, ref_w, ref_h = get_reference_box(box, ref_box_type)

    # Resolve offsets (top, right, bottom, left)
    top_offset = resolve_position_value(offsets[0], ref_h)
    right_offset = resolve_position_value(offsets[1], ref_w)
    bottom_offset = resolve_position_value(offsets[2], ref_h)
    left_offset = resolve_position_value(offsets[3], ref_w)

    # Calculate absolute bounds of the inset rectangle
    inset_left = ref_x + left_offset
    inset_top = ref_y + top_offset
    inset_right = ref_x + ref_w - right_offset
    inset_bottom = ref_y + ref_h - bottom_offset

    # Resolve border-radius if present
    resolved_radius = None
    if border_radius:
        # border_radius is a tuple of 4 values (tl, tr, br, bl)
        # Resolve each to absolute pixels
        resolved_radius = tuple(
            resolve_position_value(r, min(ref_w, ref_h))
            for r in border_radius
        )

    return InsetBoundary(inset_left, inset_top, inset_right, inset_bottom,
                         resolved_radius)


def resolve_position_value(value, reference_length):
    """Resolve a position value (length or percentage) to absolute pixels.

    Args:
        value: A Dimension with unit, or a numeric value
        reference_length: The reference length for percentage calculations

    Returns:
        Absolute value in pixels (float)
    """
    if hasattr(value, 'unit'):
        if value.unit == '%':
            return value.value * reference_length / 100
        elif value.unit == 'px':
            return value.value
        elif value.unit is None:
            # Unitless value (e.g., 0)
            return value.value
        elif value.unit in LENGTHS_TO_PIXELS:
            # Convert absolute length units (in, cm, mm, pt, pc, q) to pixels
            return value.value * LENGTHS_TO_PIXELS[value.unit]
        else:
            # For unknown units, treat as pixels (best effort)
            return value.value
    return float(value)


def resolve_shape_radius(radius_spec, ref_w, ref_h, cx, cy, ref_x, ref_y):
    """Resolve a circle shape radius keyword or value.

    Args:
        radius_spec: 'closest-side', 'farthest-side', or Dimension
        ref_w, ref_h: Reference box width and height
        cx, cy: Center coordinates (absolute)
        ref_x, ref_y: Reference box position (absolute)

    Returns:
        Absolute radius value (float)
    """
    if isinstance(radius_spec, str):
        if radius_spec == 'closest-side':
            # Distance to closest side from center
            return min(
                cx - ref_x,           # left side
                ref_x + ref_w - cx,   # right side
                cy - ref_y,           # top side
                ref_y + ref_h - cy    # bottom side
            )
        elif radius_spec == 'farthest-side':
            return max(
                cx - ref_x,
                ref_x + ref_w - cx,
                cy - ref_y,
                ref_y + ref_h - cy
            )
    elif hasattr(radius_spec, 'unit'):
        if radius_spec.unit == 'px':
            return radius_spec.value
        elif radius_spec.unit == '%':
            # For circle percentage, resolve against:
            # sqrt(width^2 + height^2) / sqrt(2)
            ref_length = math.sqrt(ref_w**2 + ref_h**2) / math.sqrt(2)
            return radius_spec.value * ref_length / 100
        elif radius_spec.unit is None:
            return radius_spec.value
        elif radius_spec.unit in LENGTHS_TO_PIXELS:
            # Convert absolute length units (in, cm, mm, pt, pc, q) to pixels
            return radius_spec.value * LENGTHS_TO_PIXELS[radius_spec.unit]
        else:
            # For unknown units, treat as pixels (best effort)
            return radius_spec.value

    return 0  # Fallback


def resolve_ellipse_radius(radius_spec, ref_w, ref_h, cx, cy, ref_x, ref_y,
                           is_horizontal=True):
    """Resolve an ellipse radius keyword or value.

    Args:
        radius_spec: 'closest-side', 'farthest-side', or Dimension
        ref_w, ref_h: Reference box width and height
        cx, cy: Center coordinates (absolute)
        ref_x, ref_y: Reference box position (absolute)
        is_horizontal: True for rx (horizontal radius), False for ry

    Returns:
        Absolute radius value (float)
    """
    if isinstance(radius_spec, str):
        if radius_spec == 'closest-side':
            if is_horizontal:
                return min(cx - ref_x, ref_x + ref_w - cx)
            else:
                return min(cy - ref_y, ref_y + ref_h - cy)
        elif radius_spec == 'farthest-side':
            if is_horizontal:
                return max(cx - ref_x, ref_x + ref_w - cx)
            else:
                return max(cy - ref_y, ref_y + ref_h - cy)
    elif hasattr(radius_spec, 'unit'):
        if radius_spec.unit == 'px':
            return radius_spec.value
        elif radius_spec.unit == '%':
            # For ellipse percentage, resolve against the
            # corresponding reference axis
            ref_length = ref_w if is_horizontal else ref_h
            return radius_spec.value * ref_length / 100
        elif radius_spec.unit is None:
            return radius_spec.value
        elif radius_spec.unit in LENGTHS_TO_PIXELS:
            # Convert absolute length units (in, cm, mm, pt, pc, q) to pixels
            return radius_spec.value * LENGTHS_TO_PIXELS[radius_spec.unit]
        else:
            # For unknown units, treat as pixels (best effort)
            return radius_spec.value

    return 0  # Fallback
