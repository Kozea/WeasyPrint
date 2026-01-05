"""Fetch and decode images in various formats."""

import io
import math
import struct
from hashlib import md5
from io import BytesIO
from itertools import cycle
from pathlib import Path
from xml.etree import ElementTree

import pydyf
from PIL import Image, ImageFile, ImageOps
from tinycss2.color5 import parse_color

from . import DEFAULT_OPTIONS
from .layout.percent import percentage
from .logger import LOGGER
from .svg import SVG
from .urls import URLFetchingError, fetch

# Don’t crash when converting truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True


class ImageLoadingError(ValueError):
    """An error occured when loading an image.

    The image data is probably corrupted or in an invalid format.

    """


class RasterImage:
    def __init__(self, pillow_image, image_id, image_data, filename=None,
                 cache=None, orientation='none', options=DEFAULT_OPTIONS):
        # Transpose image
        original_pillow_image = pillow_image
        pillow_image = rotate_pillow_image(pillow_image, orientation)
        if original_pillow_image is not pillow_image:
            # Keep image format as it is discarded by transposition
            pillow_image.format = original_pillow_image.format
            # Discard original data, as the image has been transformed
            image_data = filename = None

        self.id = image_id
        self._cache = {} if cache is None else cache
        self._jpeg_quality = jpeg_quality = options['jpeg_quality']
        self._dpi = options['dpi']

        if 'transparency' in pillow_image.info:
            pillow_image = pillow_image.convert('RGBA')
        elif pillow_image.mode in ('1', 'P', 'I'):
            pillow_image = pillow_image.convert('RGB')

        self.mode = pillow_image.mode
        self.width = pillow_image.width
        self.height = pillow_image.height
        self.ratio = (self.width / self.height) if self.height != 0 else math.inf
        self.optimize = optimize = options['optimize_images']

        # The presence of the APP14 segment indicates an Adobe image with
        # inverted CMYK data. Specify a Decode Array to invert it again back to
        # normal. See PR #2179.
        app14 = getattr(original_pillow_image, 'app', {}).get('APP14')
        self.invert_colors = self.mode == 'CMYK' and app14 is not None

        if pillow_image.format in ('JPEG', 'MPO'):
            self.format = 'JPEG'
            if image_data is None or optimize or jpeg_quality is not None:
                image_file = io.BytesIO()
                options = {'format': 'JPEG', 'optimize': optimize}
                if self._jpeg_quality is not None:
                    options['quality'] = self._jpeg_quality
                pillow_image.save(image_file, **options)
                image_data = image_file.getvalue()
                filename = None
        else:
            self.format = 'PNG'
            if image_data is None or optimize or pillow_image.format != 'PNG':
                image_file = io.BytesIO()
                pillow_image.save(image_file, format='PNG', optimize=optimize)
                image_data = image_file.getvalue()
                filename = None
        self.image_data = self.cache_image_data(image_data, filename)

    def get_intrinsic_size(self, resolution, font_size):
        return self.width / resolution, self.height / resolution, self.ratio

    def draw(self, stream, concrete_width, concrete_height, style):
        if self.width <= 0 or self.height <= 0:
            return

        image_rendering = style['image_rendering']
        interpolate = image_rendering == 'auto'
        ratio = 1
        if self._dpi:
            pt_to_in = 4 / 3 / 96
            width_inches = abs(concrete_width * stream.ctm[0][0] * pt_to_in)
            height_inches = abs(concrete_height * stream.ctm[1][1] * pt_to_in)
            dpi = max(self.width / width_inches, self.height / height_inches)
            if dpi > self._dpi:
                ratio = self._dpi / dpi
        image_name = stream.add_image(self, interpolate, ratio)

        stream.transform(
            concrete_width, 0, 0, -concrete_height, 0, concrete_height)
        stream.draw_x_object(image_name)

    def cache_image_data(self, data, filename=None, slot='source'):
        if filename:
            return LazyLocalImage(filename)
        else:
            key = f'{self.id}-{slot}-{self._dpi or ""}'
            return LazyImage(self._cache, key, data)

    def get_x_object(self, interpolate, dpi_ratio):
        if dpi_ratio == 1:
            width, height = self.width, self.height
        else:
            thumbnail = Image.open(io.BytesIO(self.image_data.data))
            width = max(1, round(self.width * dpi_ratio))
            height = max(1, round(self.height * dpi_ratio))
            thumbnail.thumbnail((width, height))
            image_file = io.BytesIO()
            thumbnail.save(
                image_file, format=thumbnail.format, optimize=self.optimize)
            width, height = thumbnail.width, thumbnail.height
            self.image_data = self.cache_image_data(image_file.getvalue())

        if self.mode in ('RGB', 'RGBA'):
            color_space = '/DeviceRGB'
        elif self.mode in ('L', 'LA'):
            color_space = '/DeviceGray'
        elif self.mode == 'CMYK':
            color_space = '/DeviceCMYK'
        else:
            LOGGER.warning('Unknown image mode: %s', self.mode)
            color_space = '/DeviceRGB'

        extra = pydyf.Dictionary({
            'Type': '/XObject',
            'Subtype': '/Image',
            'Width': width,
            'Height': height,
            'ColorSpace': color_space,
            'BitsPerComponent': 8,
            'Interpolate': 'true' if interpolate else 'false',
        })

        if self.format == 'JPEG':
            if self.invert_colors:
                extra['Decode'] = pydyf.Array((1, 0) * 4)
            extra['Filter'] = '/DCTDecode'
            return pydyf.Stream([self.image_data], extra)

        extra['Filter'] = '/FlateDecode'
        extra['DecodeParms'] = pydyf.Dictionary({
            # Predictor 15 specifies that we're providing PNG data,
            # ostensibly using an "optimum predictor", but doesn't actually
            # matter as long as the predictor value is 10+ according to the
            # spec. (Other PNG predictor values assert that we're using
            # specific predictors that we don't want to commit to, but
            # "optimum" can vary.)
            'Predictor': 15,
            'Columns': width,
        })
        if self.mode in ('RGB', 'RGBA'):
            # Defaults to 1.
            extra['DecodeParms']['Colors'] = 3
        if self.mode in ('RGBA', 'LA'):
            # Remove alpha channel from image
            pillow_image = Image.open(io.BytesIO(self.image_data.data))
            alpha = pillow_image.getchannel('A')
            pillow_image = pillow_image.convert(self.mode[:-1])
            png_data = self._get_png_data(pillow_image)
            # Save alpha channel as mask
            alpha_data = self._get_png_data(alpha)
            stream = self.cache_image_data(alpha_data, slot='streamalpha')
            extra['SMask'] = pydyf.Stream([stream], extra={
                'Filter': '/FlateDecode',
                'Type': '/XObject',
                'Subtype': '/Image',
                'DecodeParms': pydyf.Dictionary({
                    'Predictor': 15,
                    'Columns': width,
                }),
                'Width': width,
                'Height': height,
                'ColorSpace': '/DeviceGray',
                'BitsPerComponent': 8,
                'Interpolate': 'true' if interpolate else 'false',
            })
        else:
            png_data = self._get_png_data(
                Image.open(io.BytesIO(self.image_data.data)))

        return pydyf.Stream([self.cache_image_data(png_data, slot='stream')], extra)

    @staticmethod
    def _get_png_data(pillow_image):
        image_file = BytesIO()
        pillow_image.save(image_file, format='PNG')

        # Read the PNG header, then discard it because we know it's a PNG. If
        # this weren't just output from Pillow, we should actually check it.
        image_file.seek(8)

        png_data = []
        raw_chunk_length = image_file.read(4)
        # PNG files consist of a series of chunks.
        while raw_chunk_length:
            # Each chunk begins with its data length (four bytes, may be zero),
            # then its type (four ASCII characters), then the data, then four
            # bytes of a CRC.
            chunk_length, = struct.unpack('!I', raw_chunk_length)
            chunk_type = image_file.read(4)
            if chunk_type == b'IDAT':
                png_data.append(image_file.read(chunk_length))
            else:
                image_file.seek(chunk_length, io.SEEK_CUR)
            # We aren't checking the CRC, we assume this is a valid PNG.
            image_file.seek(4, io.SEEK_CUR)
            raw_chunk_length = image_file.read(4)

        return b''.join(png_data)


class LazyImage(pydyf.Object):
    def __init__(self, cache, key, data):
        super().__init__()
        self._key = key
        self._cache = cache
        cache[key] = data

    @property
    def data(self):
        return self._cache[self._key]


class LazyLocalImage(pydyf.Object):
    def __init__(self, filename):
        super().__init__()
        self._filename = filename

    @property
    def data(self):
        return Path(self._filename).read_bytes()


class SVGImage:
    def __init__(self, tree, base_url, url_fetcher, context):
        font_config = context.font_config if context else None
        self._svg = SVG(tree, base_url, font_config, url_fetcher)
        self._base_url = base_url
        self._url_fetcher = url_fetcher
        self._context = context

    def get_intrinsic_size(self, image_resolution, font_size):
        width, height = self._svg.get_intrinsic_size(font_size)
        if None in (width, height):
            viewbox = self._svg.get_viewbox()
            if viewbox and viewbox[2] and viewbox[3]:
                ratio = viewbox[2] / viewbox[3]
                if width:
                    height = width / ratio
                elif height:
                    width = height * ratio
            else:
                ratio = None
        elif width and height:
            ratio = width / height
        else:
            ratio = 1
        return width, height, ratio

    def draw(self, stream, concrete_width, concrete_height, _style):
        try:
            self._svg.draw(
                stream, concrete_width, concrete_height, self._base_url,
                self._context)
        except BaseException as exception:
            LOGGER.error('Failed to render SVG image %s', self._base_url)
            LOGGER.debug('Error while rendering SVG image:', exc_info=exception)


def get_image_from_uri(cache, url_fetcher, options, url, forced_mime_type=None,
                       context=None, orientation='from-image'):
    """Get an Image instance from an image URI."""
    if url in cache:
        return cache[url]

    try:
        with fetch(url_fetcher, url) as response:
            bytestring = response.read()
            mime_type = forced_mime_type or response.content_type

        image = None
        svg_exceptions = []
        # Try to rely on given mimetype for SVG
        if mime_type == 'image/svg+xml':
            try:
                tree = ElementTree.fromstring(bytestring)
                image = SVGImage(tree, url, url_fetcher, context)
            except Exception as svg_exception:
                svg_exceptions.append(svg_exception)
        # Try pillow for raster images, or for failing SVG
        if image is None:
            try:
                pillow_image = Image.open(BytesIO(bytestring))
            except Exception as raster_exception:
                if mime_type == 'image/svg+xml':
                    # Tried SVGImage then Pillow for a SVG, abort
                    raise ImageLoadingError from svg_exceptions[0]
                try:
                    # Last chance, try SVG
                    tree = ElementTree.fromstring(bytestring)
                    image = SVGImage(tree, url, url_fetcher, context)
                except Exception:
                    # Tried Pillow then SVGImage for a raster, abort
                    raise ImageLoadingError from raster_exception
            else:
                # Store image id to enable cache in Stream.add_image
                image_id = md5(url.encode(), usedforsecurity=False).hexdigest()
                image = RasterImage(
                    pillow_image, image_id, bytestring, response.path, cache,
                    orientation, options)

    except (URLFetchingError, ImageLoadingError) as exception:
        LOGGER.error('Failed to load image at %r: %s', url, exception)
        LOGGER.debug('Error while loading image:', exc_info=exception)
        image = None

    cache[url] = image
    return image


def rotate_pillow_image(pillow_image, orientation):
    """Return a copy of a Pillow image with modified orientation.

    If orientation is not changed, return the same image.

    """
    image_format = pillow_image.format
    if orientation == 'from-image':
        if 'exif' in pillow_image.info:
            pillow_image = ImageOps.exif_transpose(pillow_image)
    elif orientation != 'none':
        angle, flip = orientation
        if angle > 0:
            rotation = getattr(Image.Transpose, f'ROTATE_{angle}')
            pillow_image = pillow_image.transpose(rotation)
        if flip:
            pillow_image = pillow_image.transpose(
                Image.Transpose.FLIP_LEFT_RIGHT)

    # Keep image format as it is discarded by transposition
    pillow_image.format = image_format
    return pillow_image


def process_color_stops(vector_length, positions, hints, style):
    """Give color stops positions and hints on the gradient vector.

    ``vector_length`` is the distance between the starting point and ending
    point of the vector gradient.

    ``positions`` is a list of ``None``, or ``Dimension`` in px or %. 0 is the
    starting point, 1 the ending point.

    See https://drafts.csswg.org/css-images-3/#color-stop-syntax.

    Return processed color stops, as a list of floats in px.

    """
    # Resolve percentages.
    positions = [percentage(position, style, vector_length) for position in positions]
    hints = [percentage(hint, style, vector_length) / vector_length for hint in hints]

    # First and last default to 100%.
    if positions[0] is None:
        positions[0] = 0
    if positions[-1] is None:
        positions[-1] = vector_length

    # Make sure positions are increasing.
    previous_pos = positions[0]
    for i, position in enumerate(positions):
        if position is not None:
            if position < previous_pos:
                positions[i] = previous_pos
            else:
                previous_pos = position

    # Assign missing values.
    previous_i = -1
    for i, position in enumerate(positions):
        if position is not None:
            base = positions[previous_i]
            increment = (position - base) / (i - previous_i)
            for j in range(previous_i + 1, i):
                positions[j] = base + j * increment
            previous_i = i

    # Calculate exponential value for PDF hints, avoid big numbers.
    hints = [
        0 if hint <= 0 else
        2 ** 32 if hint >= 1 else
        min(2 ** 32, math.log(0.5, hint)) for hint in hints]

    return positions, hints


def normalize_stop_positions(positions):
    """Normalize stop positions between 0 and 1.

    Return ``(first, last, positions)``.

    first: original position of the first position.
    last: original position of the last position.
    positions: list of positions between 0 and 1.

    """
    first, last = positions[0], positions[-1]
    total_length = last - first
    if total_length == 0:
        positions = [0] * len(positions)
    else:
        positions = [(pos - first) / total_length for pos in positions]
    return first, last, positions


def gradient_average_color(colors, positions):
    """
    https://drafts.csswg.org/css-images-3/#gradient-average-color
    """
    # TODO: handle color spaces.
    nb_stops = len(positions)
    assert nb_stops > 1
    assert nb_stops == len(colors)
    total_length = positions[-1] - positions[0]
    if total_length == 0:
        positions = list(range(nb_stops))
        total_length = nb_stops - 1
    premul_r = [r * a for r, g, b, a in colors]
    premul_g = [g * a for r, g, b, a in colors]
    premul_b = [b * a for r, g, b, a in colors]
    alpha = [a for r, g, b, a in colors]
    result_r = result_g = result_b = result_a = 0
    total_weight = 2 * total_length
    for i, position in enumerate(positions[1:], 1):
        weight = (position - positions[i - 1]) / total_weight
        for j in (i - 1, i):
            result_r += premul_r[j] * weight
            result_g += premul_g[j] * weight
            result_b += premul_b[j] * weight
            result_a += alpha[j] * weight
    # Un-premultiply.
    if result_a == 0:
        return parse_color('transparent')
    else:
        return parse_color(
            f'rgb({result_r / result_a * 255} {result_g / result_a * 255} '
            f'{result_b / result_a * 255}/{ result_a })')


class Gradient:
    def __init__(self, color_stops, repeating, color_hints):
        assert color_stops
        # List of (r, g, b, a)
        self.colors = tuple(color for color, _ in color_stops)
        # List of Dimensions
        self.stop_positions = tuple(position for _, position in color_stops)
        # List of Dimensions
        self.color_hints = color_hints
        # Boolean
        self.repeating = repeating

    def get_intrinsic_size(self, image_resolution, font_size):
        return None, None, None

    def draw(self, stream, concrete_width, concrete_height, style):
        scale_y, type_, points, positions, colors, color_hints = self.layout(
            concrete_width, concrete_height, style)

        if type_ == 'solid':
            stream.rectangle(0, 0, concrete_width, concrete_height)
            stream.set_color(colors[0])
            stream.fill()
            return

        alphas = [color[3] for color in colors]
        alpha_couples = [
            [alphas[i], alphas[i + 1], color_hints[i]]
            for i in range(len(alphas) - 1)]
        # TODO: handle other color spaces.
        color_couples = [
            [colors[i].to('srgb')[:3], colors[i + 1].to('srgb')[:3], color_hints[i]]
            for i in range(len(colors) - 1)]

        # Premultiply colors
        for i, alpha in enumerate(alphas):
            if alpha == 0:
                if i > 0:
                    color_couples[i - 1][1] = color_couples[i - 1][0]
                if i < len(colors) - 1:
                    color_couples[i][0] = color_couples[i][1]
        for i, (a0, a1, hint) in enumerate(alpha_couples):
            if 0 not in (a0, a1) and (a0, a1) != (1, 1):
                color_couples[i][2] = a0 / a1

        shading_type = 2 if type_ == 'linear' else 3
        domain = (positions[0], positions[-1])
        extend = not self.repeating
        encode = (len(colors) - 1) * (0, 1)
        bounds = positions[1:-1]
        sub_functions = (
            stream.create_interpolation_function((0, 1), c0, c1, hint)
            for c0, c1, hint in color_couples)
        function = stream.create_stitching_function(
            domain, encode, bounds, sub_functions)
        # TODO: handle other color spaces.
        shading = stream.add_shading(
            shading_type, 'RGB', domain, points, extend, function)
        stream.transform(d=scale_y)

        if any(alpha != 1 for alpha in alphas):
            alpha_stream = stream.set_alpha_state(
                0, 0, concrete_width, concrete_height)

            shading_type = 2 if type_ == 'linear' else 3
            sub_functions = (
                stream.create_interpolation_function((0, 1), (c0,), (c1,), hint)
                for c0, c1, hint in alpha_couples)
            function = stream.create_stitching_function(
                domain, encode, bounds, sub_functions)
            alpha_shading = alpha_stream.add_shading(
                shading_type, 'Gray', domain, points, extend, function)
            alpha_stream.transform(d=scale_y)
            alpha_stream.stream = [f'/{alpha_shading.id} sh']

        stream.paint_shading(shading.id)

    def layout(self, width, height, style):
        """Get layout information about the gradient.

        width, height: Gradient box. Top-left is at coordinates (0, 0).
        style: box computed style.

        Returns (scale_y, type_, points, positions, colors).

        scale_y: vertical scale of the gradient. float, used for ellipses
                 radial gradients. 1 otherwise.
        type_: gradient type.
        points: coordinates of useful points, depending on type_:
            'solid': None.
            'linear': (x0, y0, x1, y1)
                      coordinates of the starting and ending points.
            'radial': (cx0, cy0, radius0, cx1, cy1, radius1)
                      coordinates of the starting end ending circles
        positions: positions of the color stops. list of floats in between 0
                   and 1 (0 at the starting point, 1 at the ending point).
        colors: list of (r, g, b, a).

        """
        raise NotImplementedError


class LinearGradient(Gradient):
    def __init__(self, color_stops, direction, repeating, color_hints):
        super().__init__(color_stops, repeating, color_hints)
        # ('corner', keyword) or ('angle', radians)
        self.direction_type, self.direction = direction

    def layout(self, width, height, style):
        # Only one color, render the gradient as a solid color
        if len(self.colors) == 1:
            return 1, 'solid', None, [], [self.colors[0]], []

        # Define the (dx, dy) unit vector giving the direction of the gradient.
        # Positive dx: right, positive dy: down.
        if self.direction_type == 'corner':
            y, x = self.direction.split('_')
            factor_x = -1 if x == 'left' else 1
            factor_y = -1 if y == 'top' else 1
            diagonal = math.hypot(width, height)
            # Note the direction swap: dx based on height, dy based on width
            # The gradient line is perpendicular to a diagonal.
            dx = factor_x * height / diagonal
            dy = factor_y * width / diagonal
        else:
            assert self.direction_type == 'angle'
            angle = self.direction  # 0 upwards, then clockwise
            dx = math.sin(angle)
            dy = -math.cos(angle)

        # Round dx and dy to avoid floating points errors caused by
        # trigonometry and angle units conversions
        dx, dy = round(dx, 9), round(dy, 9)

        # Normalize colors positions
        colors = list(self.colors)
        vector_length = abs(width * dx) + abs(height * dy)
        positions, hints = process_color_stops(
            vector_length, self.stop_positions, self.color_hints, style)
        if not self.repeating:
            # Add explicit colors at boundaries if needed, because PDF doesn’t
            # extend color stops that are not displayed
            if positions[0] == positions[1]:
                positions.insert(0, positions[0] - 1)
                colors.insert(0, colors[0])
                hints.insert(0, 1)
            if positions[-2] == positions[-1]:
                positions.append(positions[-1] + 1)
                colors.append(colors[-1])
                hints.append(1)
        first, last, positions = normalize_stop_positions(positions)

        if self.repeating:
            # Render as a solid color if the first and last positions are equal
            # See https://drafts.csswg.org/css-images-3/#repeating-gradients
            if first == last:
                color = gradient_average_color(colors, positions)
                return 1, 'solid', None, [], [color], []

            # Define defined gradient length and steps between positions
            stop_length = last - first
            assert stop_length > 0
            position_steps = [
                positions[i + 1] - positions[i]
                for i in range(len(positions) - 1)]

            # Create cycles used to add colors
            next_steps = cycle((0, *position_steps))
            next_colors = cycle(colors)
            next_hints = cycle(hints)
            previous_steps = cycle((0, *position_steps[::-1]))
            previous_colors = cycle(colors[::-1])
            previous_hints = cycle(hints[::-1])

            # Add colors after last step
            while last < vector_length:
                step = next(next_steps)
                colors.append(next(next_colors))
                hints.append(next(next_hints))
                positions.append(positions[-1] + step)
                last += step * stop_length

            # Add colors before first step
            while first > 0:
                step = next(previous_steps)
                colors.insert(0, next(previous_colors))
                hints.insert(0, next(previous_hints))
                positions.insert(0, positions[0] - step)
                first -= step * stop_length

        # Define the coordinates of the starting and ending points
        start_x = (width - dx * vector_length) / 2
        start_y = (height - dy * vector_length) / 2
        points = (
            start_x + dx * first, start_y + dy * first,
            start_x + dx * last, start_y + dy * last)

        return 1, 'linear', points, positions, colors, hints


class RadialGradient(Gradient):
    def __init__(self, color_stops, shape, size, center, repeating, color_hints):
        super().__init__(color_stops, repeating, color_hints)
        # Center of the ending shape. (origin_x, pos_x, origin_y, pos_y)
        self.center = center
        # Type of ending shape: 'circle' or 'ellipse'
        self.shape = shape
        # size_type: 'keyword'
        #   size: 'closest-corner', 'farthest-corner',
        #         'closest-side', or 'farthest-side'
        # size_type: 'explicit'
        #   size: (radius_x, radius_y)
        self.size_type, self.size = size

    def layout(self, width, height, style):
        # Only one color, render the gradient as a solid color
        if len(self.colors) == 1:
            return 1, 'solid', None, [], [self.colors[0]], []

        # Define the center of the gradient
        origin_x, center_x, origin_y, center_y = self.center
        center_x = percentage(center_x, style, width)
        center_y = percentage(center_y, style, height)
        if origin_x == 'right':
            center_x = width - center_x
        if origin_y == 'bottom':
            center_y = height - center_y

        # Resolve sizes and vertical scale
        size_x, size_y = self._handle_degenerate(
            *self._resolve_size(width, height, center_x, center_y, style))
        scale_y = size_y / size_x

        # Normalize colors positions
        colors = list(self.colors)
        positions, hints = process_color_stops(
            size_x, self.stop_positions, self.color_hints, style)
        if not self.repeating:
            # Add explicit colors at boundaries if needed, because PDF doesn’t
            # extend color stops that are not displayed
            if positions[0] > 0 and positions[0] == positions[1]:
                positions.insert(0, 0)
                colors.insert(0, colors[0])
                hints.insert(0, 1)
            if positions[-2] == positions[-1]:
                positions.append(positions[-1] + 1)
                colors.append(colors[-1])
                hints.append(1)
        if positions[0] < 0:
            # PDF doesn’t like negative radiuses, shift into the positive realm
            if self.repeating:
                # Add vector lengths to first position until positive
                vector_length = positions[-1] - positions[0]
                offset = vector_length * (1 + (-positions[0] // vector_length))
                positions = [position + offset for position in positions]
            else:
                # Only keep colors with position >= 0, interpolate if needed
                if positions[-1] <= 0:
                    # All stops are negative, fill with the last color
                    return 1, 'solid', None, [], [self.colors[-1]], []
                for i, position in enumerate(positions):
                    if position == 0:
                        # Keep colors and positions from this rank
                        colors, positions = colors[i:], positions[i:]
                        break
                    if position > 0:
                        # Interpolate with previous rank to get color at 0
                        color = colors[i]
                        previous_color = colors[i - 1]
                        previous_position = positions[i - 1]
                        assert previous_position < 0
                        intermediate_color = gradient_average_color(
                            [previous_color, previous_color, color, color],
                            [previous_position, 0, 0, position])
                        colors = [intermediate_color, *colors[i:]]
                        positions = [0, *positions[i:]]
                        break
        first, last, positions = normalize_stop_positions(positions)

        # Render as a solid color if the first and last positions are the same
        # See https://drafts.csswg.org/css-images-3/#repeating-gradients
        if first == last and self.repeating:
            color = gradient_average_color(colors, positions)
            return 1, 'solid', None, [], [color], []

        # Define the coordinates of the gradient circles
        points = (
            center_x, center_y / scale_y, first,
            center_x, center_y / scale_y, last)

        if self.repeating:
            points, positions, colors, hints = self._repeat(
                width, height, scale_y, points, positions, colors, hints)

        return scale_y, 'radial', points, positions, colors, hints

    def _repeat(self, width, height, scale_y, points, positions, colors, hints):
        # Keep original lists and values, they’re useful
        original_colors = colors.copy()
        original_hints = hints.copy()
        original_positions = positions.copy()
        gradient_length = points[5] - points[2]

        # Get the maximum distance between the center and the corners, to find
        # how many times we have to repeat the colors outside
        max_distance = max(
            math.hypot(width - points[0], height / scale_y - points[1]),
            math.hypot(width - points[0], -points[1] * scale_y),
            math.hypot(-points[0], height / scale_y - points[1]),
            math.hypot(-points[0], -points[1] * scale_y))
        repeat_after = math.ceil((max_distance - points[5]) / gradient_length)
        if repeat_after > 0:
            # Repeat colors and extrapolate positions
            repeat = 1 + repeat_after
            colors *= repeat
            hints = ([*hints, 1] * repeat)[:-1]
            positions = [
                i + position for i in range(repeat) for position in positions]
            points = (*points[:5], points[5] + gradient_length * repeat_after)

        if points[2] == 0:
            # Inner circle has 0 radius, no need to repeat inside, return
            return points, positions, colors, hints

        # Find how many times we have to repeat the colors inside
        repeat_before = points[2] / gradient_length

        # Set the inner circle size to 0
        points = (*points[:2], 0, *points[3:])

        # Find how many times the whole gradient can be repeated
        full_repeat = int(repeat_before)
        if full_repeat:
            # Repeat colors and extrapolate positions
            colors += original_colors * full_repeat
            hints += [1, *original_hints] * full_repeat
            positions = [
                i - full_repeat + position for i in range(full_repeat)
                for position in original_positions] + positions

        # Find the ratio of gradient that must be added to reach the center
        partial_repeat = repeat_before - full_repeat
        if partial_repeat == 0:
            # No partial repeat, return
            return points, positions, colors, hints

        # Iterate through positions in reverse order, from the outer
        # circle to the original inner circle, to find positions from
        # the inner circle (including full repeats) to the center
        assert (original_positions[0], original_positions[-1]) == (0, 1)
        assert 0 < partial_repeat < 1
        reverse = original_positions[::-1]
        ratio = 1 - partial_repeat
        for i, position in enumerate(reverse, start=1):
            if position == ratio:
                # The center is a color of the gradient, truncate original
                # colors and positions and prepend them
                colors = original_colors[-i:] + colors
                hints = [*original_hints[-i:], 1, *hints]
                new_positions = [
                    position - full_repeat - 1
                    for position in original_positions[-i:]]
                positions = new_positions + positions
                return points, positions, colors, hints
            if position < ratio:
                # The center is between two colors of the gradient,
                # define the center color as the average of these two
                # gradient colors
                color = original_colors[-i]
                next_color = original_colors[-(i - 1)]
                next_position = original_positions[-(i - 1)]
                average_colors = [color, color, next_color, next_color]
                average_positions = [position, ratio, ratio, next_position]
                zero_color = gradient_average_color(average_colors, average_positions)
                colors = [zero_color, *original_colors[-(i-1):], *colors]
                hints = [1, *original_hints[-(i-1):], 1, *hints]
                new_positions = [
                    position - 1 - full_repeat for position
                    in original_positions[-(i - 1):]]
                positions = (ratio - 1 - full_repeat, *new_positions, *positions)
                return points, positions, colors, hints

    def _resolve_size(self, width, height, center_x, center_y, style):
        """Resolve circle size of the radial gradient."""
        if self.size_type == 'explicit':
            size_x, size_y = self.size
            size_x = percentage(size_x, style, width)
            size_y = percentage(size_y, style, height)
            return size_x, size_y
        left = abs(center_x)
        right = abs(width - center_x)
        top = abs(center_y)
        bottom = abs(height - center_y)
        pick = min if self.size.startswith('closest') else max
        if self.size.endswith('side'):
            if self.shape == 'circle':
                size_xy = pick(left, right, top, bottom)
                return size_xy, size_xy
            # else: ellipse
            return pick(left, right), pick(top, bottom)
        # else: corner
        if self.shape == 'circle':
            size_xy = pick(math.hypot(left, top), math.hypot(left, bottom),
                           math.hypot(right, top), math.hypot(right, bottom))
            return size_xy, size_xy
        # else: ellipse
        corner_x, corner_y = pick(
            (left, top), (left, bottom), (right, top), (right, bottom),
            key=lambda a: math.hypot(*a))
        return corner_x * math.sqrt(2), corner_y * math.sqrt(2)

    def _handle_degenerate(self, size_x, size_y):
        """Handle degenerate radial gradients.

        See https://drafts.csswg.org/css-images-3/#degenerate-radials

        """
        if size_x == size_y == 0:
            size_x = size_y = 1e-7
        elif size_x == 0:
            size_x = 1e-7
            size_y = 1e7
        elif size_y == 0:
            size_x = 1e7
            size_y = 1e-7
        return size_x, size_y
