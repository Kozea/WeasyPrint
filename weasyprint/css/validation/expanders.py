"""Validate properties expanders."""

import functools

from tinycss2.ast import DimensionToken, IdentToken, NumberToken
from tinycss2.color5 import parse_color

from ..functions import check_var
from ..properties import INITIAL_VALUES
from .descriptors import expand_font_variant

from ..tokens import (  # isort:skip
    InvalidValues, Pending, get_keyword, get_single_keyword, split_on_comma)
from .properties import (  # isort:skip
    background_attachment, background_image, background_position, background_repeat,
    background_size, block_ellipsis, border_image_source, border_image_slice,
    border_image_width, border_image_outset, border_image_repeat, border_style,
    border_width, box, column_count, column_width, flex_basis, flex_direction,
    flex_grow_shrink, flex_wrap, font_family, font_size, font_stretch, font_style,
    font_variant_caps, font_weight, gap, grid_line, grid_template, line_height,
    list_style_image, list_style_position, list_style_type, mask_border_mode,
    other_colors, overflow_wrap, text_decoration_thickness, validate_non_shorthand)

EXPANDERS = {}


class PendingExpander(Pending):
    """Expander with validation done when defining calculated values."""
    def __init__(self, tokens, validator):
        super().__init__(tokens, validator.keywords['name'])
        self.validator = validator

    def validate(self, tokens, wanted_key):
        for key, value in self.validator(tokens):
            if key.startswith('-'):
                key = f'{self.validator.keywords["name"]}{key}'
            if key == wanted_key:
                return value
        raise KeyError


def _find_var(tokens, expander, expanded_names):
    """Return pending expanders when var is found in tokens."""
    for token in tokens:
        if check_var(token):
            # Found CSS variable, keep pending-substitution values.
            pending = PendingExpander(tokens, expander)
            return {name: pending for name in expanded_names}


def expander(property_name):
    """Decorator adding a function to the ``EXPANDERS``."""
    def expander_decorator(function):
        """Add ``function`` to the ``EXPANDERS``."""
        assert property_name not in EXPANDERS, property_name
        EXPANDERS[property_name] = function
        return function
    return expander_decorator


def generic_expander(*expanded_names, **kwargs):
    """Decorator helping expanders to handle ``inherit`` and ``initial``.

    Wrap an expander so that it does not have to handle the 'inherit' and
    'initial' cases, and can just yield name suffixes. Missing suffixes
    get the initial value.

    """
    wants_base_url = kwargs.pop('wants_base_url', False)
    assert not kwargs

    def generic_expander_decorator(wrapped):
        """Decorate the ``wrapped`` expander."""
        @functools.wraps(wrapped)
        def generic_expander_wrapper(tokens, name, base_url):
            """Wrap the expander."""
            expander = functools.partial(
                generic_expander_wrapper, name=name, base_url=base_url)

            skip_validation = False
            keyword = get_single_keyword(tokens)
            if keyword in ('inherit', 'initial'):
                results = {name: keyword for name in expanded_names}
                skip_validation = True
            else:
                results = _find_var(tokens, expander, expanded_names)
                if results:
                    skip_validation = True

            if not skip_validation:
                results = {}
                if wants_base_url:
                    result = wrapped(tokens, name, base_url)
                else:
                    result = wrapped(tokens, name)
                for new_name, new_token in result:
                    assert new_name in expanded_names, new_name
                    if new_name in results:
                        raise InvalidValues(
                            f'got multiple {new_name.strip("-")} values '
                            f'in a {name} shorthand')
                    results[new_name] = new_token

            for new_name in expanded_names:
                if new_name.startswith('-'):
                    # new_name is a suffix
                    actual_new_name = f'{name}{new_name}'
                else:
                    actual_new_name = new_name

                if new_name in results:
                    value = results[new_name]
                    if not skip_validation:
                        # validate_non_shorthand returns ((name, value),)
                        (actual_new_name, value), = validate_non_shorthand(
                            value, actual_new_name, base_url, required=True)
                else:
                    value = 'initial'

                yield actual_new_name, value
        return generic_expander_wrapper
    return generic_expander_decorator


@expander('border-color')
@expander('border-style')
@expander('border-width')
@expander('margin')
@expander('padding')
@expander('bleed')
def expand_four_sides(tokens, name, base_url):
    """Expand properties setting a token for the four sides of a box."""
    # Define expanded names.
    expanded_names = []
    for suffix in ('-top', '-right', '-bottom', '-left'):
        if (i := name.rfind('-')) == -1:
            expanded_names.append(f'{name}{suffix}')
        else:
            # eg. border-color becomes border-*-color, not border-color-*
            expanded_names.append(f'{name[:i]}{suffix}{name[i:]}')

    # Return pending expanders if var is found.
    expander = functools.partial(
        expand_four_sides, name=name, base_url=base_url)
    if result := _find_var(tokens, expander, expanded_names):
        yield from result.items()
        return

    # Make sure we have 4 tokens.
    if len(tokens) == 1:
        tokens *= 4
    elif len(tokens) == 2:
        tokens *= 2  # (bottom, left) defaults to (top, right)
    elif len(tokens) == 3:
        tokens += (tokens[1],)  # left defaults to right
    elif len(tokens) != 4:
        raise InvalidValues(
            f'Expected 1 to 4 token components got {len(tokens)}')
    for expanded_name, token in zip(expanded_names, tokens):
        # validate_non_shorthand returns ((name, value),), we want
        # to yield (name, value).
        result, = validate_non_shorthand(
            [token], expanded_name, base_url, required=True)
        yield result


@expander('border-radius')
@generic_expander(
    'border-top-left-radius', 'border-top-right-radius',
    'border-bottom-right-radius', 'border-bottom-left-radius',
    wants_base_url=True)
def border_radius(tokens, name, base_url):
    """Validator for the ``border-radius`` property."""
    current = horizontal = []
    vertical = []
    for token in tokens:
        if token.type == 'literal' and token.value == '/':
            if current is horizontal:
                if token == tokens[-1]:
                    raise InvalidValues('Expected value after "/" separator')
                else:
                    current = vertical
            else:
                raise InvalidValues('Expected only one "/" separator')
        else:
            current.append(token)

    if not vertical:
        vertical = horizontal[:]

    for values in horizontal, vertical:
        # Make sure we have 4 tokens
        if len(values) == 1:
            values *= 4
        elif len(values) == 2:
            values *= 2  # (br, bl) defaults to (tl, tr)
        elif len(values) == 3:
            values.append(values[1])  # bl defaults to tr
        elif len(values) != 4:
            raise InvalidValues(
                f'Expected 1 to 4 token components got {len(values)}')
    corners = ('top-left', 'top-right', 'bottom-right', 'bottom-left')
    for corner, tokens in zip(corners, zip(horizontal, vertical)):
        name = f'border-{corner}-radius'
        validate_non_shorthand(tokens, name, base_url, required=True)
        yield name, tokens


@expander('list-style')
@generic_expander('-type', '-position', '-image', wants_base_url=True)
def expand_list_style(tokens, name, base_url):
    """Expand the ``list-style`` shorthand property.

    See https://www.w3.org/TR/CSS21/generate.html#propdef-list-style

    """
    type_specified = image_specified = False
    none_count = 0
    for token in tokens:
        if get_keyword(token) == 'none':
            # Can be either -style or -image, see at the end which is not
            # otherwise specified.
            none_count += 1
            none_token = token
            continue

        if list_style_image([token], base_url) is not None:
            suffix = '-image'
            image_specified = True
        elif list_style_position([token]) is not None:
            suffix = '-position'
        elif list_style_type([token]) is not None:
            suffix = '-type'
            type_specified = True
        else:
            raise InvalidValues
        yield suffix, [token]

    if not type_specified and none_count:
        yield '-type', [none_token]
        none_count -= 1

    if not image_specified and none_count:
        yield '-image', [none_token]
        none_count -= 1

    if none_count:
        # Too many none tokens.
        raise InvalidValues


@expander('border')
def expand_border(tokens, name, base_url):
    """Expand the ``border`` shorthand property.

    See https://www.w3.org/TR/CSS21/box.html#propdef-border

    """
    for suffix in ('-top', '-right', '-bottom', '-left'):
        yield from expand_border_side(tokens, name + suffix, base_url)


@expander('border-top')
@expander('border-right')
@expander('border-bottom')
@expander('border-left')
@expander('column-rule')
@expander('outline')
@generic_expander('-width', '-color', '-style')
def expand_border_side(tokens, name):
    """Expand the ``border-*`` shorthand properties.

    See https://www.w3.org/TR/CSS21/box.html#propdef-border-top

    """
    for token in tokens:
        if parse_color(token) is not None:
            suffix = '-color'
        elif border_width([token]) is not None:
            suffix = '-width'
        elif border_style([token]) is not None:
            suffix = '-style'
        else:
            raise InvalidValues
        yield suffix, [token]


@expander('border-image')
@generic_expander('-outset', '-repeat', '-slice', '-source', '-width',
                  wants_base_url=True)
def expand_border_image(tokens, name, base_url):
    """Expand the ``border-image-*`` shorthand properties.

    See https://drafts.csswg.org/css-backgrounds/#the-border-image

    """
    tokens = list(tokens)
    while tokens:
        if border_image_source(tokens[:1], base_url):
            yield '-source', [tokens.pop(0)]
        elif border_image_repeat(tokens[:1]):
            repeats = [tokens.pop(0)]
            while tokens and border_image_repeat(tokens[:1]):
                repeats.append(tokens.pop(0))
            yield '-repeat', repeats
        elif border_image_slice(tokens[:1]) or get_keyword(tokens[0]) == 'fill':
            slices = [tokens.pop(0)]
            while tokens and border_image_slice(slices + tokens[:1]):
                slices.append(tokens.pop(0))
            yield '-slice', slices
            if tokens and tokens[0].type == 'literal' and tokens[0].value == '/':
                # slices / *
                tokens.pop(0)
            else:
                # slices other
                continue
            if not tokens:
                # slices /
                raise InvalidValues
            if border_image_width(tokens[:1]):
                widths = [tokens.pop(0)]
                while tokens and border_image_width(widths + tokens[:1]):
                    widths.append(tokens.pop(0))
                yield '-width', widths
                if tokens and tokens[0].type == 'literal' and tokens[0].value == '/':
                    # slices / widths / slash *
                    tokens.pop(0)
                else:
                    # slices / widths other
                    continue
            elif tokens and tokens[0].type == 'literal' and tokens[0].value == '/':
                # slices / / *
                tokens.pop(0)
            else:
                # slices / other
                raise InvalidValues
            if not tokens:
                # slices / * /
                raise InvalidValues
            if border_image_outset(tokens[:1]):
                outsets = [tokens.pop(0)]
                while tokens and border_image_outset(outsets + tokens[:1]):
                    outsets.append(tokens.pop(0))
                yield '-outset', outsets
            else:
                # slash / * / other
                raise InvalidValues
        else:
            raise InvalidValues


@expander('mask-border')
@generic_expander('-outset', '-repeat', '-slice', '-source', '-width', '-mode',
                  wants_base_url=True)
def expand_mask_border(tokens, name, base_url):
    """Expand the ``mask-border-*`` shorthand properties.

    See https://drafts.fxtf.org/css-masking/#the-mask-border

    """
    tokens = list(tokens)
    while tokens:
        if border_image_source(tokens[:1], base_url):
            yield '-source', [tokens.pop(0)]
        elif mask_border_mode(tokens[:1]):
            yield '-mode', [tokens.pop(0)]
        elif border_image_repeat(tokens[:1]):
            repeats = [tokens.pop(0)]
            while tokens and border_image_repeat(tokens[:1]):
                repeats.append(tokens.pop(0))
            yield '-repeat', repeats
        elif border_image_slice(tokens[:1]) or get_keyword(tokens[0]) == 'fill':
            slices = [tokens.pop(0)]
            while tokens and border_image_slice(slices + tokens[:1]):
                slices.append(tokens.pop(0))
            yield '-slice', slices
            if tokens and tokens[0].type == 'literal' and tokens[0].value == '/':
                # slices / *
                tokens.pop(0)
            else:
                # slices other
                continue
            if not tokens:
                # slices /
                raise InvalidValues
            if border_image_width(tokens[:1]):
                widths = [tokens.pop(0)]
                while tokens and border_image_width(widths + tokens[:1]):
                    widths.append(tokens.pop(0))
                yield '-width', widths
                if tokens and tokens[0].type == 'literal' and tokens[0].value == '/':
                    # slices / widths / slash *
                    tokens.pop(0)
                else:
                    # slices / widths other
                    continue
            elif tokens and tokens[0].type == 'literal' and tokens[0].value == '/':
                # slices / / *
                tokens.pop(0)
            else:
                # slices / other
                raise InvalidValues
            if not tokens:
                # slices / * /
                raise InvalidValues
            if border_image_outset(tokens[:1]):
                outsets = [tokens.pop(0)]
                while tokens and border_image_outset(outsets + tokens[:1]):
                    outsets.append(tokens.pop(0))
                yield '-outset', outsets
            else:
                # slash / * / other
                raise InvalidValues
        else:
            raise InvalidValues


@expander('background')
def expand_background(tokens, name, base_url):
    """Expand the ``background`` shorthand property.

    See https://drafts.csswg.org/css-backgrounds-3/#the-background

    """
    expanded_names = (
        'background-color', 'background-image', 'background-repeat',
        'background-attachment', 'background-position', 'background-size',
        'background-clip', 'background-origin')
    keyword = get_single_keyword(tokens)
    if keyword in ('initial', 'inherit'):
        for name in expanded_names:
            yield name, keyword
        return

    expander = functools.partial(
        expand_background, name=name, base_url=base_url)
    if result := _find_var(tokens, expander, expanded_names):
        yield from result.items()
        return

    def parse_layer(tokens, final_layer=False):
        results = {}

        def add(name, value):
            if value is None:
                return False
            name = f'background-{name}'
            if name in results:
                raise InvalidValues
            results[name] = value
            return True

        # Make `tokens` a stack
        tokens = tokens[::-1]
        while tokens:
            if add('repeat',
                   background_repeat.single_value(tokens[-2:][::-1])):
                del tokens[-2:]
                continue
            token = tokens[-1:]
            if final_layer and add('color', other_colors(token)):
                tokens.pop()
                continue
            if add('image', background_image.single_value(token, base_url)):
                tokens.pop()
                continue
            if add('repeat', background_repeat.single_value(token)):
                tokens.pop()
                continue
            if add('attachment', background_attachment.single_value(token)):
                tokens.pop()
                continue
            for n in (4, 3, 2, 1)[-len(tokens):]:
                n_tokens = tokens[-n:][::-1]
                position = background_position.single_value(n_tokens)
                if position is not None:
                    assert add('position', position)
                    del tokens[-n:]
                    if (tokens and tokens[-1].type == 'literal' and
                            tokens[-1].value == '/'):
                        for n in (3, 2)[-len(tokens):]:
                            # n includes the '/' delimiter.
                            n_tokens = tokens[-n:-1][::-1]
                            size = background_size.single_value(n_tokens)
                            if size is not None:
                                assert add('size', size)
                                del tokens[-n:]
                    break
            if position is not None:
                continue
            if add('origin', box.single_value(token)):
                tokens.pop()
                next_token = tokens[-1:]
                if add('clip', box.single_value(next_token)):
                    tokens.pop()
                else:
                    # The same keyword sets both
                    add('clip', box.single_value(token))
                continue
            raise InvalidValues

        color = results.pop(
            'background-color', INITIAL_VALUES['background_color'])
        for name in expanded_names:
            if name not in results and name != 'background-color':
                results[name] = INITIAL_VALUES[name.replace('-', '_')][0]
        return color, results

    layers = reversed(split_on_comma(tokens))
    color, last_layer = parse_layer(next(layers), final_layer=True)
    results = {key: [value] for key, value in last_layer.items()}
    for tokens in layers:
        _, layer = parse_layer(tokens)
        for name, value in layer.items():
            results[name].append(value)
    for name, values in results.items():
        yield name, values[::-1]  # "Un-reverse"
    yield 'background-color', color


@expander('text-decoration')
@generic_expander('-line', '-color', '-style', '-thickness')
def expand_text_decoration(tokens, name):
    """Expand the ``text-decoration`` shorthand property."""
    line = []
    color = []
    style = []
    thickness = []
    none_in_line = False

    for token in tokens:
        keyword = get_keyword(token)
        if keyword in ('none', 'underline', 'overline', 'line-through', 'blink'):
            line.append(token)
            if none_in_line:
                raise InvalidValues
            elif keyword == 'none':
                none_in_line = True
        elif keyword in ('solid', 'double', 'dotted', 'dashed', 'wavy'):
            if style:
                raise InvalidValues
            style.append(token)
        elif parse_color(token):
            if color:
                raise InvalidValues
            color.append(token)
        elif text_decoration_thickness([token]):
            if thickness:
                raise InvalidValues
            thickness.append(token)
        else:
            raise InvalidValues

    if line:
        yield '-line', line
    if color:
        yield '-color', color
    if style:
        yield '-style', style
    if thickness:
        yield '-thickness', thickness


def expand_page_break_before_after(tokens, name):
    """Expand legacy ``page-break-before`` and ``page-break-after`` properties.

    See https://www.w3.org/TR/css-break-3/#page-break-properties

    """
    keyword = get_single_keyword(tokens)
    new_name = name.split('-', 1)[1]
    if keyword in ('auto', 'left', 'right', 'avoid'):
        yield new_name, tokens
    elif keyword == 'always':
        token = IdentToken(
            tokens[0].source_line, tokens[0].source_column, 'page')
        yield new_name, [token]
    else:
        raise InvalidValues


@expander('page-break-after')
@generic_expander('break-after')
def expand_page_break_after(tokens, name):
    """Expand legacy ``page-break-after`` property.

    See https://www.w3.org/TR/css-break-3/#page-break-properties

    """
    return expand_page_break_before_after(tokens, name)


@expander('page-break-before')
@generic_expander('break-before')
def expand_page_break_before(tokens, name):
    """Expand legacy ``page-break-before`` property.

    See https://www.w3.org/TR/css-break-3/#page-break-properties

    """
    return expand_page_break_before_after(tokens, name)


@expander('page-break-inside')
@generic_expander('break-inside')
def expand_page_break_inside(tokens, name):
    """Expand the legacy ``page-break-inside`` property.

    See https://www.w3.org/TR/css-break-3/#page-break-properties

    """
    keyword = get_single_keyword(tokens)
    if keyword in ('auto', 'avoid'):
        yield 'break-inside', tokens
    else:
        raise InvalidValues


@expander('columns')
@generic_expander('column-width', 'column-count')
def expand_columns(tokens, name):
    """Expand the ``columns`` shorthand property."""
    name = None
    if len(tokens) == 2 and get_keyword(tokens[0]) == 'auto':
        tokens = tokens[::-1]
    for token in tokens:
        if column_width([token]) is not None and name != 'column-width':
            name = 'column-width'
        elif column_count([token]) is not None:
            name = 'column-count'
        else:
            raise InvalidValues
        yield name, [token]
    if len(tokens) == 1:
        name = 'column-width' if name == 'column-count' else 'column-count'
        token = IdentToken(
            tokens[0].source_line, tokens[0].source_column, 'auto')
        yield name, [token]


@expander('font-variant')
@generic_expander('-alternates', '-caps', '-east-asian', '-ligatures',
                  '-numeric', '-position')
def font_variant(tokens, name):
    """Expand the ``font-variant`` shorthand property.

    https://www.w3.org/TR/css-fonts-3/#font-variant-prop

    """
    return expand_font_variant(tokens)


@expander('font')
@generic_expander('-style', '-variant-caps', '-weight', '-stretch', '-size',
                  'line-height', '-family')  # line-height is not a suffix
def expand_font(tokens, name):
    """Expand the ``font`` shorthand property.

    https://www.w3.org/TR/css-fonts-3/#font-prop

    """
    expand_font_keyword = get_single_keyword(tokens)
    if expand_font_keyword in ('caption', 'icon', 'menu', 'message-box',
                               'small-caption', 'status-bar'):
        raise InvalidValues('System fonts are not supported')

    # Make `tokens` a stack
    tokens = list(reversed(tokens))
    # Values for font-style, font-variant-caps, font-weight and font-stretch
    # can come in any order and are all optional.
    for _ in range(4):
        token = tokens.pop()
        if get_keyword(token) == 'normal':
            # Just ignore 'normal' keywords. Unspecified properties will get
            # their initial token, which is 'normal' for all four here.
            continue

        if font_style([token]) is not None:
            suffix = '-style'
        elif font_variant_caps([token]) is not None:
            suffix = '-variant-caps'
        elif font_weight([token]) is not None:
            suffix = '-weight'
        elif font_stretch([token]) is not None:
            suffix = '-stretch'
        else:
            # We’re done with these four, continue with font-size
            break
        yield suffix, [token]

        if not tokens:
            raise InvalidValues
    else:
        if not tokens:
            raise InvalidValues
        token = tokens.pop()

    # Then font-size is mandatory
    # Latest `token` from the loop.
    if font_size([token]) is None:
        raise InvalidValues
    yield '-size', [token]

    # Then line-height is optional, but font-family is not so the list
    # must not be empty yet
    if not tokens:
        raise InvalidValues

    token = tokens.pop()
    if token.type == 'literal' and token.value == '/':
        token = tokens.pop()
        if line_height([token]) is None:
            raise InvalidValues
        yield 'line-height', [token]
    else:
        # We pop()ed a font-family, add it back
        tokens.append(token)

    # Reverse the stack to get normal list
    tokens.reverse()
    if font_family(tokens) is None:
        raise InvalidValues
    yield '-family', tokens


@expander('word-wrap')
@generic_expander('overflow-wrap')
def expand_word_wrap(tokens, name):
    """Expand the ``word-wrap`` legacy property.

    See https://www.w3.org/TR/css-text-3/#overflow-wrap

    """
    keyword = overflow_wrap(tokens)
    if keyword is None:
        raise InvalidValues
    yield 'overflow-wrap', tokens


@expander('flex')
@generic_expander('-grow', '-shrink', '-basis')
def expand_flex(tokens, name):
    """Expand the ``flex`` property."""
    keyword = get_single_keyword(tokens)
    if keyword == 'none':
        line, column = tokens[0].source_line, tokens[0].source_column
        zero_token = NumberToken(line, column, 0, 0, '0')
        auto_token = IdentToken(line, column, 'auto')
        yield '-grow', [zero_token]
        yield '-shrink', [zero_token]
        yield '-basis', [auto_token]
    else:
        grow, shrink, basis = 1, 1, None
        grow_found, shrink_found, basis_found = False, False, False
        for token in tokens:
            # "A unitless zero that is not already preceded by two flex factors
            # must be interpreted as a flex factor."
            forced_flex_factor = (
                token.type == 'number' and token.int_value == 0 and
                not all((grow_found, shrink_found)))
            if not basis_found and not forced_flex_factor:
                new_basis = flex_basis([token])
                if new_basis is not None:
                    basis = token
                    basis_found = True
                    continue
            if not grow_found:
                new_grow = flex_grow_shrink([token])
                if new_grow is None:
                    raise InvalidValues
                else:
                    grow = new_grow
                    grow_found = True
                    continue
            elif not shrink_found:
                new_shrink = flex_grow_shrink([token])
                if new_shrink is None:
                    raise InvalidValues
                else:
                    shrink = new_shrink
                    shrink_found = True
                    continue
            else:
                raise InvalidValues
        line, column = tokens[0].source_line, tokens[0].source_column
        int_grow = int(grow) if float(grow).is_integer() else None
        int_shrink = int(shrink) if float(shrink).is_integer() else None
        grow_token = NumberToken(line, column, grow, int_grow, str(grow))
        shrink_token = NumberToken(
            line, column, shrink, int_shrink, str(shrink))
        if not basis_found:
            basis = DimensionToken(line, column, 0, 0, '0', 'px')
        yield '-grow', [grow_token]
        yield '-shrink', [shrink_token]
        yield '-basis', [basis]


@expander('flex-flow')
@generic_expander('flex-direction', 'flex-wrap')
def expand_flex_flow(tokens, name):
    """Expand the ``flex-flow`` property."""
    if len(tokens) == 2:
        for sorted_tokens in tokens, tokens[::-1]:
            direction = flex_direction([sorted_tokens[0]])
            wrap = flex_wrap([sorted_tokens[1]])
            if direction and wrap:
                yield 'flex-direction', [sorted_tokens[0]]
                yield 'flex-wrap', [sorted_tokens[1]]
                break
        else:
            raise InvalidValues
    elif len(tokens) == 1:
        direction = flex_direction([tokens[0]])
        if direction:
            yield 'flex-direction', [tokens[0]]
        else:
            wrap = flex_wrap([tokens[0]])
            if wrap:
                yield 'flex-wrap', [tokens[0]]
            else:
                raise InvalidValues
    else:
        raise InvalidValues


def _expand_grid_template(tokens, name):
    line, column = tokens[0].source_line, tokens[0].source_column
    none = IdentToken(line, column, 'none')
    if len(tokens) == 1 and get_keyword(tokens[0]) == 'none':
        yield '-columns', [none]
        yield '-rows', [none]
        yield '-areas', [none]
        return
    slash_separated = [[]]
    for token in tokens:
        if token.type == 'literal' and token.value == '/':
            slash_separated.append([])
        else:
            slash_separated[-1].append(token)
    if len(slash_separated) == 2:
        rows = grid_template(slash_separated[0])
        columns = grid_template(slash_separated[1])
        if columns:
            if rows:
                yield '-columns', slash_separated[1]
                yield '-rows', slash_separated[0]
                yield '-areas', [none]
                return
            columns = slash_separated[1]
        else:
            raise InvalidValues
    elif len(slash_separated) == 1:
        columns = [none]
    else:
        raise InvalidValues
    # TODO: Handle last syntax.
    raise InvalidValues


@expander('grid-template')
@generic_expander('-columns', '-rows', '-areas')
def expand_grid_template(tokens, name):
    """Expand the ``grid-template`` property."""
    yield from _expand_grid_template(tokens, name)


@expander('grid')
@generic_expander('-template-columns', '-template-rows', '-template-areas',
                  '-auto-columns', '-auto-rows', '-auto-flow')
def expand_grid(tokens, name):
    """Expand the ``grid`` property."""
    line, column = tokens[0].source_line, tokens[0].source_column
    auto = IdentToken(line, column, 'auto')
    none = IdentToken(line, column, 'none')
    row = IdentToken(line, column, 'row')
    column = IdentToken(line, column, 'column')
    try:
        template = tuple(_expand_grid_template(tokens, 'grid-template'))
    except InvalidValues:
        pass
    else:
        for key, value in template:
            yield f'-template-{key.split("-")[-1]}', value
        yield '-auto-columns', [auto]
        yield '-auto-rows', [auto]
        yield '-auto-flow', [row]
        return
    split_tokens = [[]]
    for token in tokens:
        if token.type == 'literal' and token.value == '/':
            split_tokens.append([])
            continue
        split_tokens[-1].append(token)
    if len(split_tokens) != 2:
        raise InvalidValues
    auto_track = None
    dense = None
    templates = {'row': [], 'column': []}
    iterable = zip(split_tokens, templates.items())
    for tokens, (track, track_templates) in iterable:
        auto_flow_token = False
        for token in tokens:
            if get_keyword(token) == 'dense':
                if dense or (auto_track and auto_track != track):
                    raise InvalidValues
                dense = token
                auto_track = track
            elif get_keyword(token) == 'auto-flow':
                if auto_flow_token or (auto_track and auto_track != track):
                    raise InvalidValues
                auto_flow_token = True
                auto_track = track
            elif token == tokens[-1]:
                track_templates.append(token)
            else:
                raise InvalidValues
    if not auto_track:
        raise InvalidValues
    non_auto_track = 'row' if auto_track == 'column' else 'column'
    auto_track_token = column if auto_track == 'column' else row
    yield '-auto-flow', (
        (auto_track_token, dense) if dense else (auto_track_token,))
    yield f'-auto-{auto_track}s', tuple(templates[auto_track])
    yield f'-auto-{non_auto_track}s', [auto]
    yield f'-template-{auto_track}s', [none]
    yield f'-template-{non_auto_track}s', tuple(templates[non_auto_track])
    yield '-template-areas', [none]


def _expand_grid_column_row_area(tokens, max_number):
    grid_lines = [[]]
    for token in tokens:
        if token.type == 'literal' and token.value == '/':
            grid_lines.append([])
            continue
        grid_lines[-1].append(token)
    if not 1 <= len(grid_lines) <= max_number:
        raise InvalidValues
    validations = []
    for tokens in grid_lines:
        if not (validation := grid_line(tokens)):
            raise InvalidValues
        validations.append(validation)
        yield tuple(tokens)
    auto = IdentToken(token.source_line, token.source_column, 'auto')
    if (lines := len(grid_lines)) <= 1:
        custom_ident = set(validations[0][:2]) == {None}
        value = tuple(grid_lines[0]) if custom_ident else (auto,)
        grid_lines.append(tokens)
        validations.append(validations[0])
        yield value
    if lines <= 2 < max_number:
        custom_ident = set(validations[0][:2]) == {None}
        yield tuple(grid_lines[0]) if custom_ident else (auto,)
    if lines <= 3 < max_number:
        custom_ident = set(validations[1][:2]) == {None}
        yield tuple(grid_lines[1]) if custom_ident else (auto,)


@expander('grid-column')
@expander('grid-row')
@generic_expander('-start', '-end')
def expand_grid_column_row(tokens, name):
    """Expand the ``grid-[column|row]`` properties."""
    tokens_list = _expand_grid_column_row_area(tokens, 2)
    for tokens, side in zip(tokens_list, ('start', 'end')):
        yield f'-{side}', tokens


@expander('grid-area')
@generic_expander('grid-row-start', 'grid-row-end',
                  'grid-column-start', 'grid-column-end')
def expand_grid_area(tokens, name):
    """Expand the ``grid-area`` property."""
    tokens_list = _expand_grid_column_row_area(tokens, 4)
    sides = ('row-start', 'column-start', 'row-end', 'column-end')
    for tokens, side in zip(tokens_list, sides):
        yield f'grid-{side}', tokens


@expander('grid-gap')
@expander('gap')
@generic_expander('column-gap', 'row-gap')
def expand_gap(tokens, name):
    """Expand the ``gap`` property."""
    if len(tokens) == 1:
        if gap(tokens) is None:
            raise InvalidValues
        yield 'row-gap', tokens
        yield 'column-gap', tokens
    elif len(tokens) == 2:
        column_gap, row_gap = gap(tokens[0:1]), gap(tokens[1:2])
        if None in (column_gap, row_gap):
            raise InvalidValues
        yield 'row-gap', tokens[0:1]
        yield 'column-gap', tokens[1:2]
    else:
        raise InvalidValues


@expander('grid-column-gap')
@generic_expander('column-gap')
def expand_legacy_column_gap(tokens, name):
    """Expand legacy ``grid-column-gap`` property."""
    keyword = gap(tokens)
    if keyword is None:
        raise InvalidValues
    yield 'column-gap', tokens


@expander('grid-row-gap')
@generic_expander('row-gap')
def expand_legacy_row_gap(tokens, name):
    """Expand legacy ``grid-row-gap`` property."""
    keyword = gap(tokens)
    if keyword is None:
        raise InvalidValues
    yield 'row-gap', tokens


@expander('place-content')
@generic_expander('align-content', 'justify-content')
def expand_place_content(tokens, name):
    """Expand the ``place-content`` property."""
    # TODO
    raise InvalidValues


@expander('place-items')
@generic_expander('align-items', 'justify-items')
def expand_place_items(tokens, name):
    """Expand the ``place-items`` property."""
    # TODO
    raise InvalidValues


@expander('place-self')
@generic_expander('align-self', 'justify-self')
def expand_place_self(tokens, name):
    """Expand the ``place-self`` property."""
    # TODO
    raise InvalidValues


@expander('line-clamp')
@generic_expander('max-lines', 'continue', 'block-ellipsis')
def expand_line_clamp(tokens, name):
    """Expand the ``line-clamp`` property."""
    if len(tokens) == 1:
        keyword = get_single_keyword(tokens)
        if keyword == 'none':
            line, column = tokens[0].source_line, tokens[0].source_column
            none_token = IdentToken(line, column, 'none')
            auto_token = IdentToken(line, column, 'auto')
            yield 'max-lines', [none_token]
            yield 'continue', [auto_token]
            yield 'block-ellipsis', [none_token]
        elif tokens[0].type == 'number' and tokens[0].int_value is not None:
            line, column = tokens[0].source_line, tokens[0].source_column
            auto_token = IdentToken(line, column, 'auto')
            discard_token = IdentToken(line, column, 'discard')
            yield 'max-lines', [tokens[0]]
            yield 'continue', [discard_token]
            yield 'block-ellipsis', [auto_token]
        else:
            raise InvalidValues
    elif len(tokens) == 2:
        if tokens[0].type == 'number':
            max_lines = tokens[0].int_value
            ellipsis = block_ellipsis([tokens[1]])
            if max_lines and ellipsis is not None:
                line, column = tokens[0].source_line, tokens[0].source_column
                discard_token = IdentToken(line, column, 'discard')
                yield 'max-lines', [tokens[0]]
                yield 'continue', [discard_token]
                yield 'block-ellipsis', [tokens[1]]
            else:
                raise InvalidValues
        else:
            raise InvalidValues
    else:
        raise InvalidValues


@expander('text-align')
@generic_expander('-all', '-last')
def expand_text_align(tokens, name):
    """Expand the ``text-align`` property."""
    if len(tokens) == 1:
        keyword = get_single_keyword(tokens)
        if keyword is None:
            raise InvalidValues
        if keyword == 'justify-all':
            line, column = tokens[0].source_line, tokens[0].source_column
            align_all = IdentToken(line, column, 'justify')
        else:
            align_all = tokens[0]
        yield '-all', [align_all]
        if keyword == 'justify':
            line, column = tokens[0].source_line, tokens[0].source_column
            align_last = IdentToken(line, column, 'start')
        else:
            align_last = align_all
        yield '-last', [align_last]
    else:
        raise InvalidValues
