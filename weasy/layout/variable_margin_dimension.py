# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""
Margin box variable dimension computation.

http://dev.w3.org/csswg/css3-page/#margin-dimension

"""

from __future__ import division


def with_rule_2(side_boxes, outer_sum, intrinsic):
    """Margin box variable dimension computation, in the case where
    rule 2 applies.
    """
    result = 'again'
    while result == 'again':
        implementation, swap_ac = IMPLEMENTATIONS[
            tuple(box.inner == 'auto' for box in side_boxes),
            tuple('auto' in [box.margin_a, box.margin_b] for box in side_boxes),
        ]
        if swap_ac:
            box_c, box_b, box_a = side_boxes
            # TODO: find a better way to do this?
            for box in [box_a, box_c]:
                box.margin_a, box.margin_b = box.margin_b, box.margin_a
        else:
            box_a, box_b, box_c = side_boxes
        result = implementation(box_a, box_b, box_c, outer_sum, intrinsic)
        if swap_ac:
            for box in [box_a, box_c]:
                box.margin_a, box.margin_b = box.margin_b, box.margin_a

        # XXX
        if result is NotImplemented:
            for box in side_boxes:
                for attr in ['margin_a', 'margin_b', 'inner']:
                    if getattr(box, attr) == 'auto':
                        setattr(box, attr, 0)
                        import logging
                        logging.getLogger('WEASYPRINT').error(
                            '%s was left to auto on %r', attr, box)
            return


IMPLEMENTATIONS = {}


def register(auto_inners, auto_margins):
    """Register an implementation for with_rule_2()

    :param auto_inners:
        A tuple of 3 booleans. True if box A, B and C (respectively) have a
        value of 'auto' for the inner dimension.
    :param auto_margins:
        A tuple of 3 booleans. True if the box has any margin with
        the value 'auto'.

    """
    keys = set([
        ((auto_inners, auto_margins), False),
        ((auto_inners[::-1], auto_margins[::-1]), True),
    ])
    def decorator(function):
        key_1 = auto_inners, auto_margins
        keys = [(key_1, False)]
        # symmetry:
        key_2 = auto_inners[::-1], auto_margins[::-1]
        if key_2 != key_1:
            keys.append((key_2, True))
        for key, swap_ac in keys:
            assert key not in IMPLEMENTATIONS, (
                'redundant implementations for %r: %r' % (key, function))
            IMPLEMENTATIONS[key] = function, swap_ac
        return function
    return decorator


def outer(box, ignore_auto=False):
    """Return the outer dimension of a box, or raise if any value is auto."""
    values = [box.inner, box.padding_plus_border, box.margin_a, box.margin_b]
    if ignore_auto:
        return sum(value for value in values if value != 'auto')
    else:
        assert 'auto' not in values
        return sum(values)


@register(auto_inners=(0, 0, 0), auto_margins=(0, 0, 0))
def implementation_1(box_a, box_b, box_c, outer_sum, intrinsic):
#    new_outer_ac = (outer_sum - outer(box_b)) / 2
#    box_a.margin_b += new_outer_ac - outer(box_a)
#    box_c.margin_a += new_outer_ac - outer(box_c)
    # Nothing is auto, over-constrained.
    box_a.margin_b = 'auto'
    box_c.margin_a = 'auto'
    return 'again'


@register(auto_inners=(0, 0, 1), auto_margins=(0, 0, 0))
def implementation_2(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented

@register(auto_inners=(0, 1, 0), auto_margins=(0, 0, 0))
def implementation_3(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 1, 1), auto_margins=(0, 0, 0))
def implementation_4(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 0, 1), auto_margins=(0, 0, 0))
def implementation_5(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 1, 1), auto_margins=(0, 0, 0))
def implementation_6(box_a, box_b, box_c, outer_sum, intrinsic):
    min_a = intrinsic.minimum(box_a)
    min_b = intrinsic.minimum(box_b)
    min_c = intrinsic.minimum(box_c)
    remaining = (
        outer_sum
        - outer(box_a, ignore_auto=True)
        - outer(box_b, ignore_auto=True)
        - outer(box_c, ignore_auto=True)
    )
    if remaining < (min_a + min_b + min_c):
        box_a.inner = min_a
        box_b.inner = min_b
        box_c.inner = min_c
        # These will be negative
        box_a.margin_b = 'auto'
        box_c.margin_a = 'auto'
        return 'again'
    # if remaining is above max, the next best thing is to ignore max
    # Use the preferred dimension as weights to distribute the space
    preferred_a = intrinsic.minimum(box_a)
    preferred_b = intrinsic.minimum(box_b)
    preferred_c = intrinsic.minimum(box_c)
    sum_preferred = preferred_a + preferred_b + preferred_c
    if sum_preferred in [0, float('inf')]:
        box_a.inner = remaining / 3
        box_b.inner = remaining / 3
        box_c.inner = remaining / 3
    else:
        box_a.inner = remaining * preferred_a / sum_preferred
        box_b.inner = remaining * preferred_b / sum_preferred
        box_c.inner = remaining * preferred_c / sum_preferred


@register(auto_inners=(0, 0, 0), auto_margins=(0, 0, 1))
def implementation_7(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 0, 1), auto_margins=(0, 0, 1))
def implementation_8(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 1, 0), auto_margins=(0, 0, 1))
def implementation_9(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 1, 1), auto_margins=(0, 0, 1))
def implementation_10(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 0, 0), auto_margins=(0, 0, 1))
def implementation_11(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 0, 1), auto_margins=(0, 0, 1))
def implementation_12(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 1, 0), auto_margins=(0, 0, 1))
def implementation_13(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 1, 1), auto_margins=(0, 0, 1))
def implementation_14(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 0, 0), auto_margins=(0, 1, 0))
def implementation_15(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 0, 1), auto_margins=(0, 1, 0))
def implementation_16(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 1, 0), auto_margins=(0, 1, 0))
def implementation_17(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 1, 1), auto_margins=(0, 1, 0))
def implementation_18(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 0, 1), auto_margins=(0, 1, 0))
def implementation_19(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 1, 1), auto_margins=(0, 1, 0))
def implementation_20(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 0, 0), auto_margins=(0, 1, 1))
def implementation_21(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 0, 1), auto_margins=(0, 1, 1))
def implementation_22(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 1, 0), auto_margins=(0, 1, 1))
def implementation_23(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 1, 1), auto_margins=(0, 1, 1))
def implementation_24(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 0, 0), auto_margins=(0, 1, 1))
def implementation_25(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 0, 1), auto_margins=(0, 1, 1))
def implementation_26(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 1, 0), auto_margins=(0, 1, 1))
def implementation_27(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 1, 1), auto_margins=(0, 1, 1))
def implementation_28(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 0, 0), auto_margins=(1, 0, 1))
def implementation_29(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 0, 1), auto_margins=(1, 0, 1))
def implementation_30(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 1, 0), auto_margins=(1, 0, 1))
def implementation_31(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 1, 1), auto_margins=(1, 0, 1))
def implementation_32(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 0, 1), auto_margins=(1, 0, 1))
def implementation_33(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 1, 1), auto_margins=(1, 0, 1))
def implementation_34(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 0, 0), auto_margins=(1, 1, 1))
def implementation_35(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 0, 1), auto_margins=(1, 1, 1))
def implementation_36(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 1, 0), auto_margins=(1, 1, 1))
def implementation_37(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(0, 1, 1), auto_margins=(1, 1, 1))
def implementation_38(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 0, 1), auto_margins=(1, 1, 1))
def implementation_39(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented


@register(auto_inners=(1, 1, 1), auto_margins=(1, 1, 1))
def implementation_40(box_a, box_b, box_c, outer_sum, intrinsic):
    return NotImplemented

assert len(IMPLEMENTATIONS) == 64
