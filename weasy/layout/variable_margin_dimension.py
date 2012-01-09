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
    box_a, box_b, box_c = side_boxes
    first = True
    while 1:
        implementation, swap = IMPLEMENTATIONS[
            tuple(box.inner == 'auto' for box in side_boxes),
            tuple('auto' in [box.margin_a, box.margin_b] for box in side_boxes),
        ]
        if swap:
            box_a, box_c = swap_ac(box_a, box_c)
        result = implementation(box_a, box_b, box_c, outer_sum, intrinsic)
        if swap:
            box_a, box_c = swap_ac(box_a, box_c)

        # XXX
        if result is NotImplemented:
            import logging
            logging.getLogger('WEASYPRINT').error(
                'Got NotImplemented for inners=%r, margins=%r',
                [box.inner for box in side_boxes],
                [(box.margin_a, box.margin_b) for box in side_boxes],
                )
            for box in side_boxes:
                for attr in ['margin_a', 'margin_b', 'inner']:
                    if getattr(box, attr) == 'auto':
                        setattr(box, attr, 0)
            return

        if result == 'ok':
            return

        assert first  # break loops
        # Try again with less constraints
        box_a.margin_b = 'auto'
        box_c.margin_a = 'auto'
        first = False


def swap_ac(box_a, box_c):
    """Swap margins A and B in each box, and return ``box_c, box_a``."""
    # TODO: find a better way to do this?
    for box in [box_a, box_c]:
        box.margin_a, box.margin_b = box.margin_b, box.margin_a
    return box_c, box_a


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


def outer(box, ignore_auto=''):
    """Return the outer dimension of a box, or raise if any value is auto."""
    result = box.padding_plus_border
    for value, type_ in [
        (box.inner, 'I'),
        (box.margin_a, 'M'),
        (box.margin_b, 'M'),
    ]:
        if value == 'auto':
            if type_ not in ignore_auto:
                assert False
        else:
            result += value
    return result


def distribute_margins(box, new_outer):
    """Set 'auto' margins on ``box`` so that the outer dimension
    is ``new_outer``.

    """
    num_auto = [box.margin_a, box.margin_b].count('auto')
    each_auto = (new_outer - outer(box, ignore_auto='M')) / num_auto
    if box.margin_a == 'auto':
        box.margin_a = each_auto
    if box.margin_b == 'auto':
        box.margin_b = each_auto


@register(auto_inners=(0, 0, 0), auto_margins=(0, 0, 0))
def implementation_1(box_a, box_b, box_c, outer_sum, intrinsic):
    outer_a = outer(box_a)
    outer_b = outer(box_b)
    outer_c = outer(box_c)
    # Rules 1 and 2
    if outer_a == outer_c and (outer_a + outer_b + outer_c) == outer_sum:
        return 'ok'
    # Nothing is auto, over-constrained.


@register(auto_inners=(0, 0, 1), auto_margins=(0, 0, 0))
def implementation_2(box_a, box_b, box_c, outer_sum, intrinsic):
    outer_a = outer(box_a)
    outer_b = outer(box_b)
    if outer_a == (outer_sum - outer_b) / 2: # Rules 1 and 2
        outer_c = outer_a  # Rule 2
        inner_c = outer_c - outer(box_c, ignore_auto='I')
        min_c = intrinsic.minimum(box_c)
        if inner_c >= min_c:
            # Ignore the preferred/maximum as the next best solution
            # is to drop that constraint.
            box_c.inner = inner_c
            return 'ok'
    # Over-constrained


@register(auto_inners=(0, 1, 0), auto_margins=(0, 0, 0))
def implementation_3(box_a, box_b, box_c, outer_sum, intrinsic):
    outer_a = outer(box_a)
    outer_c = outer(box_c)
    if outer_a == outer_c:  # Rule 2
        outer_b = outer_sum - outer_a - outer_c  # Rule 1
        inner_b = outer_b - outer(box_b, ignore_auto='I')
        min_b = intrinsic.minimum(box_b)
        if inner_b >= min_b:
            # Ignore the preferred/maximum as the next best solution
            # is to drop that constraint.
            box_b.inner = inner_b
            return 'ok'
    # Over-constrained


@register(auto_inners=(0, 1, 1), auto_margins=(0, 0, 0))
def implementation_4(box_a, box_b, box_c, outer_sum, intrinsic):
    outer_a = outer(box_a)
    outer_c = outer_a  # Rule 2
    outer_b = outer_sum - outer_a - outer_c  # Rule 1

    inner_c = outer_c - outer(box_c, ignore_auto='I')
    inner_b = outer_b - outer(box_b, ignore_auto='I')

    min_c = intrinsic.minimum(box_c)
    min_b = intrinsic.minimum(box_b)
    if inner_b >= min_b and inner_c >= min_c:
        # Ignore the preferred/maximum as the next best solution
        # is to drop these constraints.
        box_b.inner = inner_b
        box_c.inner = inner_c
        return 'ok'
    # Over-constrained


@register(auto_inners=(1, 0, 1), auto_margins=(0, 0, 0))
def implementation_5(box_a, box_b, box_c, outer_sum, intrinsic):
    outer_b = outer(box_b)
    outer_ac = outer_sum - outer_b  # Rule 1
    outer_a = outer_ac / 2  # Rule 2
    outer_c = outer_ac / 2  # Rule 2

    inner_a = outer_a - outer(box_a, ignore_auto='I')
    inner_c = outer_c - outer(box_c, ignore_auto='I')

    min_a = intrinsic.minimum(box_a)
    min_c = intrinsic.minimum(box_c)
    if inner_a >= min_a and inner_c >= min_c:
        # Ignore the preferred/maximum as the next best solution
        # is to drop these constraints.
        box_a.inner = inner_a
        box_c.inner = inner_c
        return 'ok'
    # Over-constrained


@register(auto_inners=(1, 1, 1), auto_margins=(0, 0, 0))
def implementation_6(box_a, box_b, box_c, outer_sum, intrinsic):
    constants_a = outer(box_a, ignore_auto='I')
    constants_b = outer(box_b, ignore_auto='I')
    constants_c = outer(box_c, ignore_auto='I')

    min_outer_a = intrinsic.minimum(box_a) + constants_a
    min_outer_b = intrinsic.minimum(box_b) + constants_b
    min_outer_c = intrinsic.minimum(box_c) + constants_c

    max_a = intrinsic.preferred(box_a)
    max_b = intrinsic.preferred(box_b)
    max_c = intrinsic.preferred(box_c)
    max_outer_a = max_a + constants_a
    max_outer_b = max_b + constants_b
    max_outer_c = max_c + constants_c

    # Same for A and C, rule 2:
    min_outer_ac = max(min_outer_a, min_outer_c)
    max_outer_ac = min(max_outer_a, max_outer_c)
    # Condition 1
    if outer_sum >= (2 * min_outer_ac + min_outer_b):
        weight_ac = max(max_a, max_c)
        weight_b = max_b
        total_weight = 2 * weight_ac + weight_b  # Rule 1
        if total_weight in (0, float('inf')):
            normalized_weight_b = 1 / 3
        else:
            normalized_weight_b = weight_b / total_weight
        inner_sum = outer_sum - constants_a - constants_b - constants_c
        inner_b = inner_sum * normalized_weight_b
        outer_b = inner_b + constants_b

        new_max_outer_b = outer_sum - 2 * min_outer_ac
        # min_outer_b <= max_outer_b is ensured by Condition 1
        if (
            outer_sum <= 2 * max_outer_ac + max_outer_b and
            max_outer_a >= min_outer_c and
            max_outer_c >= min_outer_a
        ):
            # outer_ac <= max_outer_ac
            # => (outer_sum - outer_b) / 2 <= max_outer_ac
            # => outer_b >= outer_sum - 2 * max_outer_ac
            min_outer_b = max(min_outer_b, outer_sum - 2 * max_outer_ac)
            max_outer_b = min(max_outer_b, new_max_outer_b)
        else:
            # Drop max constraints
            max_outer_b = new_max_outer_b
        assert min_outer_b <= max_outer_b
        outer_b = max(outer_b, min_outer_b)
        outer_b = min(outer_b, max_outer_b)
        # Rule 1 and 2
        outer_ac = (outer_sum - outer_b) / 2
        box_a.inner = outer_ac - constants_a
        box_b.inner = outer_b - constants_b
        box_c.inner = outer_ac - constants_c

        return 'ok'

    # Over-constrained by minimums.
    # Margins that become 'auto' will end up negative.
    # Choose inner so that they are as small (close to 0) as possible.
    box_a.inner = min_outer_ac - constants_a
    box_b.inner = min_outer_b - constants_b
    box_c.inner = min_outer_ac - constants_c


@register(auto_inners=(0, 0, 0), auto_margins=(0, 0, 1))
def implementation_7(box_a, box_b, box_c, outer_sum, intrinsic):
    outer_a = outer(box_a)
    outer_b = outer(box_b)
    if outer_a == (outer_sum - outer_b) / 2: # Rules 1 and 2
        outer_c = outer_a  # Rule 2
        distribute_margins(box_c, outer_c)
        return 'ok'
    # Over-constrained


@register(auto_inners=(0, 0, 1), auto_margins=(0, 0, 1))
def implementation_8(box_a, box_b, box_c, outer_sum, intrinsic):
    outer_a = outer(box_a)
    outer_b = outer(box_b)
    if outer_a == (outer_sum - outer_b) / 2: # Rules 1 and 2
        outer_c = outer_a  # Rule 2
        remaining = outer_c - outer(box_c, ignore_auto='MI')
        min_c = intrinsic.minimum(box_c)
        max_c = intrinsic.preferred(box_c)
        if remaining < min_c:
            box_c.inner = min_c
        elif remaining > max_c:
            box_c.inner = max_c
        else:
            box_c.inner = remaining
        distribute_margins(box_c, outer_c)
        return 'ok'
    # Over-constrained


@register(auto_inners=(0, 1, 0), auto_margins=(0, 0, 1))
def implementation_9(box_a, box_b, box_c, outer_sum, intrinsic):
    outer_a = outer(box_a)
    outer_c = outer_a  # Rule 2
    outer_b = outer_sum - outer_a - outer_c  # Rule 1

    inner_b = outer_b - outer(box_b, ignore_auto='I')
    min_b = intrinsic.minimum(box_b)
    if inner_b >= min_b:
        # Ignore the preferred/maximum as the next best solution
        # is to drop that constraints.
        box_b.inner = inner_b
        distribute_margins(box_c, outer_c)
        return 'ok'
    # Over-constrained


@register(auto_inners=(0, 1, 1), auto_margins=(0, 0, 1))
def implementation_10(box_a, box_b, box_c, outer_sum, intrinsic):
    outer_a = outer(box_a)
    outer_c = outer_a  # Rule 2
    outer_b = outer_sum - outer_a - outer_c  # Rule 1

    inner_b = outer_b - outer(box_b, ignore_auto='I')

    min_b = intrinsic.minimum(box_b)
    if inner_b >= min_b:
        # Ignore the preferred/maximum as the next best solution
        # is to drop these constraints.
        box_b.inner = inner_b

        remaining_c = outer_c - outer(box_c, ignore_auto='MI')
        min_c = intrinsic.minimum(box_c)
        max_c = intrinsic.preferred(box_c)
        if remaining_c < min_c:
            box_c.inner = min_c
        elif remaining_c > max_c:
            box_c.inner = max_c
        else:
            box_c.inner = remaining_c
        distribute_margins(box_c, outer_c)
        return 'ok'
    # Over-constrained


@register(auto_inners=(1, 0, 0), auto_margins=(0, 0, 1))
def implementation_11(box_a, box_b, box_c, outer_sum, intrinsic):
    outer_b = outer(box_b)
    outer_ac = outer_sum - outer_b  # Rule 1
    outer_a = outer_ac / 2  # Rule 2
    outer_c = outer_ac / 2  # Rule 2

    inner_a = outer_a - outer(box_a, ignore_auto='I')
    min_a = intrinsic.minimum(box_a)
    if inner_a >= min_a:
        # Ignore the preferred/maximum as the next best solution
        # is to drop these constraints.
        box_a.inner = inner_a
        distribute_margins(box_c, outer_c)
        return 'ok'
    # Over-constrained


@register(auto_inners=(1, 0, 1), auto_margins=(0, 0, 1))
def implementation_12(box_a, box_b, box_c, outer_sum, intrinsic):
    outer_b = outer(box_b)
    outer_ac = outer_sum - outer_b  # Rule 1
    outer_a = outer_ac / 2  # Rule 2
    outer_c = outer_ac / 2  # Rule 2

    inner_a = outer_a - outer(box_a, ignore_auto='I')
    min_a = intrinsic.minimum(box_a)
    if inner_a >= min_a:
        # Ignore the preferred/maximum as the next best solution
        # is to drop these constraints.
        box_a.inner = inner_a

        remaining_c = outer_c - outer(box_c, ignore_auto='MI')
        min_c = intrinsic.minimum(box_c)
        max_c = intrinsic.preferred(box_c)
        if remaining_c < min_c:
            box_c.inner = min_c
        elif remaining_c > max_c:
            box_c.inner = max_c
        else:
            box_c.inner = remaining_c
        distribute_margins(box_c, outer_c)
        return 'ok'
    # Over-constrained


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
    new_outer_ac = (outer_sum - outer(box_b)) / 2
    distribute_margins(box_a, new_outer_ac)
    distribute_margins(box_c, new_outer_ac)
    return 'ok'


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
