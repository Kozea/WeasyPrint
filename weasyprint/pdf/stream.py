"""PDF stream."""

import pydyf

from ..matrix import Matrix
from ..text.ffi import ffi
from ..text.fonts import get_pango_font_key
from .fonts import Font


class Stream(pydyf.Stream):
    """PDF stream object with extra features."""
    def __init__(self, fonts, page_rectangle, states, x_objects, patterns,
                 shadings, images, mark, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_rectangle = page_rectangle
        self.marked = []
        self._fonts = fonts
        self._states = states
        self._x_objects = x_objects
        self._patterns = patterns
        self._shadings = shadings
        self._images = images
        self._mark = mark
        self._current_color = self._current_color_stroke = None
        self._current_alpha = self._current_alpha_stroke = None
        self._current_font = self._current_font_size = None
        self._old_font = self._old_font_size = None
        self._ctm_stack = [Matrix()]

        # These objects are used in text.show_first_line
        self.length = ffi.new('unsigned int *')
        self.ink_rect = ffi.new('PangoRectangle *')
        self.logical_rect = ffi.new('PangoRectangle *')

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
        super().transform(a, b, c, d, e, f)
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

    def set_color_rgb(self, r, g, b, stroke=False):
        if stroke:
            if (r, g, b) == self._current_color_stroke:
                return
            else:
                self._current_color_stroke = (r, g, b)
        else:
            if (r, g, b) == self._current_color:
                return
            else:
                self._current_color = (r, g, b)

        super().set_color_rgb(r, g, b, stroke)

    def set_font_size(self, font, size):
        if (font, size) == self._current_font:
            return
        self._current_font = (font, size)
        super().set_font_size(font, size)

    def set_state(self, state):
        key = f's{len(self._states)}'
        self._states[key] = state
        super().set_state(key)

    def set_alpha(self, alpha, stroke=False, fill=None):
        if fill is None:
            fill = not stroke

        if stroke:
            key = f'A{alpha}'
            if key != self._current_alpha_stroke:
                self._current_alpha_stroke = key
                if key not in self._states:
                    self._states[key] = pydyf.Dictionary({'CA': alpha})
                super().set_state(key)

        if fill:
            key = f'a{alpha}'
            if key != self._current_alpha:
                self._current_alpha = key
                if key not in self._states:
                    self._states[key] = pydyf.Dictionary({'ca': alpha})
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
        key = get_pango_font_key(pango_font)
        if key not in self._fonts:
            self._fonts[key] = Font(pango_font)
        return self._fonts[key]

    def add_group(self, x, y, width, height):
        states = pydyf.Dictionary()
        x_objects = pydyf.Dictionary()
        patterns = pydyf.Dictionary()
        shadings = pydyf.Dictionary()
        resources = pydyf.Dictionary({
            'ExtGState': states,
            'XObject': x_objects,
            'Pattern': patterns,
            'Shading': shadings,
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
        group = Stream(
            self._fonts, self.page_rectangle, states, x_objects, patterns,
            shadings, self._images, self._mark, extra=extra,
            compress=self.compress)
        group.id = f'x{len(self._x_objects)}'
        self._x_objects[group.id] = group
        return group

    def add_image(self, image, interpolate, ratio):
        image_name = f'i{image.id}{int(interpolate)}'
        self._x_objects[image_name] = None  # Set by write_pdf
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

    def add_pattern(self, x, y, width, height, repeat_width, repeat_height,
                    matrix):
        states = pydyf.Dictionary()
        x_objects = pydyf.Dictionary()
        patterns = pydyf.Dictionary()
        shadings = pydyf.Dictionary()
        resources = pydyf.Dictionary({
            'ExtGState': states,
            'XObject': x_objects,
            'Pattern': patterns,
            'Shading': shadings,
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
        pattern = Stream(
            self._fonts, self.page_rectangle, states, x_objects, patterns,
            shadings, self._images, self._mark, extra=extra,
            compress=self.compress)
        pattern.id = f'p{len(self._patterns)}'
        self._patterns[pattern.id] = pattern
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
        shading.id = f's{len(self._shadings)}'
        self._shadings[shading.id] = shading
        return shading

    def begin_marked_content(self, box, mcid=False, tag=None):
        if not self._mark:
            return
        property_list = None
        if tag is None:
            tag = self.get_marked_content_tag(box.element_tag)
        if mcid:
            property_list = pydyf.Dictionary({'MCID': len(self.marked)})
            self.marked.append((tag, box))
        super().begin_marked_content(tag, property_list)

    def end_marked_content(self):
        if not self._mark:
            return
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

    def get_marked_content_tag(self, element_tag):
        if element_tag == 'div':
            return 'Div'
        elif element_tag == 'span':
            return 'Span'
        elif element_tag == 'article':
            return 'Art'
        elif element_tag == 'section':
            return 'Sect'
        elif element_tag == 'blockquote':
            return 'BlockQuote'
        elif element_tag == 'p':
            return 'P'
        elif element_tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            return element_tag.upper()
        elif element_tag in ('dl', 'ul', 'ol'):
            return 'L'
        elif element_tag in ('li', 'dt', 'dd'):
            return 'LI'
        elif element_tag == 'table':
            return 'Table'
        elif element_tag in ('tr', 'th', 'td'):
            return element_tag.upper()
        elif element_tag in ('thead', 'tbody', 'tfoot'):
            return element_tag[:2].upper() + element_tag[2:]
        else:
            return 'NonStruct'
