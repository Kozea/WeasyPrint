"""PDF stream."""

from contextlib import contextmanager

import pydyf

from ..logger import LOGGER
from ..matrix import Matrix
from ..text.ffi import ffi
from ..text.fonts import get_pango_font_key
from .fonts import Font


class Stream(pydyf.Stream):
    """PDF stream object with extra features."""
    def __init__(self, fonts, page_rectangle, resources, images, tags, color_profiles,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_rectangle = page_rectangle
        self._fonts = fonts
        self._resources = resources
        self._images = images
        self._tags = tags
        self._color_profiles = color_profiles
        self._current_color = self._current_color_stroke = None
        self._current_alpha = self._current_alpha_stroke = None
        self._current_font = self._current_font_size = None
        self._old_font = self._old_font_size = None
        self._ctm_stack = [Matrix()]

        # These objects are used in text.show_first_line
        self.length = ffi.new('unsigned int *')
        self.ink_rect = ffi.new('PangoRectangle *')
        self.logical_rect = ffi.new('PangoRectangle *')

    def clone(self, **kwargs):
        if 'fonts' not in kwargs:
            kwargs['fonts'] = self._fonts
        if 'page_rectangle' not in kwargs:
            kwargs['page_rectangle'] = self.page_rectangle
        if 'resources' not in kwargs:
            kwargs['resources'] = self._resources
        if 'images' not in kwargs:
            kwargs['images'] = self._images
        if 'tags' not in kwargs:
            kwargs['tags'] = self._tags
        if 'color_profiles' not in kwargs:
            kwargs['color_profiles'] = self._color_profiles
        if 'compress' not in kwargs:
            kwargs['compress'] = self.compress
        return Stream(**kwargs)

    @property
    def ctm(self):
        return self._ctm_stack[-1]

    def push_state(self):
        super().push_state()
        self._ctm_stack.append(self.ctm)

    def pop_state(self):
        if self.stream and self.stream[-1] == b'q':
            self.stream.pop()
        else:
            super().pop_state()
        self._current_color = self._current_color_stroke = None
        self._current_alpha = self._current_alpha_stroke = None
        self._current_font = None
        self._ctm_stack.pop()
        assert self._ctm_stack

    def transform(self, a=1, b=0, c=0, d=1, e=0, f=0):
        super().set_matrix(a, b, c, d, e, f)
        self._ctm_stack[-1] = Matrix(a, b, c, d, e, f) @ self.ctm

    def begin_text(self):
        if self.stream and self.stream[-1] == b'ET':
            self._current_font = self._old_font
            self.stream.pop()
        else:
            super().begin_text()

    def end_text(self):
        self._old_font, self._current_font = self._current_font, None
        super().end_text()

    def set_color(self, color, stroke=False):
        *channels, alpha = color
        self.set_alpha(alpha, stroke)

        if stroke:
            if (color.space, *channels) == self._current_color_stroke:
                return
            else:
                self._current_color_stroke = (color.space, *channels)
        else:
            if (color.space, *channels) == self._current_color:
                return
            else:
                self._current_color = (color.space, *channels)

        if color.space in ('srgb', 'hsl', 'hwb'):
            self.set_color_rgb(*color.to('srgb').coordinates, stroke)
        elif color.space in ('xyz-d65', 'oklab', 'oklch'):
            self.set_color_space('lab-d65', stroke)
            lightness, a, b = color.to('lab').coordinates
            self.set_color_special(None, stroke, lightness, a, b)
        elif color.space in ('xyz-d50', 'lab', 'lch'):
            self.set_color_space('lab-d50', stroke)
            lightness, a, b = color.to('lab').coordinates
            self.set_color_special(None, stroke, lightness, a, b)
        elif color.space == 'device-cmyk':
            self.set_color_space('DeviceCMYK', stroke)
            c, m, y, k = color.coordinates
            self.set_color_special(None, stroke, c, m, y, k)
        elif color.space.startswith('--') and color.space in self._color_profiles:
            self.set_color_space(color.space, stroke)
            self.set_color_special(None, stroke, *color.coordinates)
        else:
            LOGGER.warning('Unsupported color space %s, use sRGB instead', color.space)
            if len(channels) > 3:
                channels = channels[:3]
            elif len(channels) == 2:
                channels = *channels, 0
            elif len(channels) == 1:
                channels = *channels, 0, 0
            self.set_color_rgb(*channels, stroke)

    def set_font_size(self, font, size):
        if (font, size) == self._current_font:
            return
        self._current_font = (font, size)
        super().set_font_size(font, size)

    def set_state(self, state):
        key = f's{len(self._resources["ExtGState"])}'
        self._resources['ExtGState'][key] = state
        super().set_state(key)

    def set_alpha(self, alpha, stroke=False, fill=None):
        if fill is None:
            fill = not stroke

        if stroke:
            key = f'A{alpha}'
            if key != self._current_alpha_stroke:
                self._current_alpha_stroke = key
                if key not in self._resources['ExtGState']:
                    self._resources['ExtGState'][key] = pydyf.Dictionary({'CA': alpha})
                super().set_state(key)

        if fill:
            key = f'a{alpha}'
            if key != self._current_alpha:
                self._current_alpha = key
                if key not in self._resources['ExtGState']:
                    self._resources['ExtGState'][key] = pydyf.Dictionary({'ca': alpha})
                super().set_state(key)

    def set_alpha_state(self, x, y, width, height, mode='luminosity'):
        alpha_stream = self.add_group(x, y, width, height)
        alpha_state = pydyf.Dictionary({
            'Type': '/ExtGState',
            'SMask': pydyf.Dictionary({
                'Type': '/Mask',
                'S': f'/{mode.capitalize()}',
                'G': alpha_stream,
            }),
            'ca': 1,
            'AIS': 'false',
        })
        self.set_state(alpha_state)
        return alpha_stream

    def set_blend_mode(self, mode):
        self.set_state(pydyf.Dictionary({
            'Type': '/ExtGState',
            'BM': f'/{mode}',
        }))

    def add_font(self, pango_font):
        key, description, font_size = get_pango_font_key(pango_font)
        if key not in self._fonts:
            self._fonts[key] = Font(pango_font, description, font_size)
        return self._fonts[key], font_size

    def add_group(self, x, y, width, height):
        resources = pydyf.Dictionary({
            'ExtGState': pydyf.Dictionary(),
            'XObject': pydyf.Dictionary(),
            'Pattern': pydyf.Dictionary(),
            'Shading': pydyf.Dictionary(),
            'ColorSpace': self._resources['ColorSpace'],
            'Font': None,  # Will be set by _use_references
        })
        extra = pydyf.Dictionary({
            'Type': '/XObject',
            'Subtype': '/Form',
            'BBox': pydyf.Array((x, y, x + width, y + height)),
            'Resources': resources,
            'Group': pydyf.Dictionary({
                'Type': '/Group',
                'S': '/Transparency',
                'I': 'true',
                'CS': '/DeviceRGB',
            }),
        })
        group = self.clone(resources=resources, extra=extra)
        group.id = f'x{len(self._resources["XObject"])}'
        self._resources['XObject'][group.id] = group
        return group

    def add_image(self, image, interpolate, ratio):
        image_name = f'i{image.id}{int(interpolate)}'
        self._resources['XObject'][image_name] = None  # Set by write_pdf
        if image_name in self._images:
            # Reuse image already stored in document
            self._images[image_name]['dpi_ratios'].add(ratio)
            return image_name

        self._images[image_name] = {
            'image': image,
            'interpolate': interpolate,
            'dpi_ratios': {ratio},
            'x_object': None,  # Set by write_pdf
        }
        return image_name

    def add_pattern(self, x, y, width, height, repeat_width, repeat_height, matrix):
        resources = pydyf.Dictionary({
            'ExtGState': pydyf.Dictionary(),
            'XObject': pydyf.Dictionary(),
            'Pattern': pydyf.Dictionary(),
            'Shading': pydyf.Dictionary(),
            'ColorSpace': self._resources['ColorSpace'],
            'Font': None,  # Will be set by _use_references
        })
        extra = pydyf.Dictionary({
            'Type': '/Pattern',
            'PatternType': 1,
            'BBox': pydyf.Array([x, y, x + width, y + height]),
            'XStep': repeat_width,
            'YStep': repeat_height,
            'TilingType': 1,
            'PaintType': 1,
            'Matrix': pydyf.Array(matrix.values),
            'Resources': resources,
        })
        pattern = self.clone(resources=resources, extra=extra)
        pattern.id = f'p{len(self._resources["Pattern"])}'
        self._resources['Pattern'][pattern.id] = pattern
        return pattern

    def add_shading(self, shading_type, color_space, domain, coords, extend,
                    function):
        shading = pydyf.Dictionary({
            'ShadingType': shading_type,
            'ColorSpace': f'/Device{color_space}',
            'Domain': pydyf.Array(domain),
            'Coords': pydyf.Array(coords),
            'Function': function,
        })
        if extend:
            shading['Extend'] = pydyf.Array((b'true', b'true'))
        shading.id = f's{len(self._resources["Shading"])}'
        self._resources['Shading'][shading.id] = shading
        return shading

    @contextmanager
    def stacked(self):
        """Save and restore stream context when used with the ``with`` keyword."""
        self.push_state()
        try:
            yield
        finally:
            self.pop_state()

    @contextmanager
    def marked(self, box, tag):
        if self._tags is not None:
            property_list = None
            mcid = len(self._tags)
            assert box not in self._tags
            self._tags[box] = {'tag': tag, 'mcid': mcid}
            property_list = pydyf.Dictionary({'MCID': mcid})
            super().begin_marked_content(tag, property_list)
        try:
            yield
        finally:
            if self._tags is not None:
                super().end_marked_content()

    @contextmanager
    def artifact(self):
        if self._tags is not None:
            super().begin_marked_content('Artifact')
        try:
            yield
        finally:
            if self._tags is not None:
                super().end_marked_content()

    @staticmethod
    def create_interpolation_function(domain, c0, c1, n):
        return pydyf.Dictionary({
            'FunctionType': 2,
            'Domain': pydyf.Array(domain),
            'C0': pydyf.Array(c0),
            'C1': pydyf.Array(c1),
            'N': n,
        })

    @staticmethod
    def create_stitching_function(domain, encode, bounds, sub_functions):
        return pydyf.Dictionary({
            'FunctionType': 3,
            'Domain': pydyf.Array(domain),
            'Encode': pydyf.Array(encode),
            'Bounds': pydyf.Array(bounds),
            'Functions': pydyf.Array(sub_functions),
        })
