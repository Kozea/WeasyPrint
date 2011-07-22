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


from ..formatting_structure import boxes
from .. import text


class LineBoxFormatting(object):
    def __init__(self, linebox):
        self.width = linebox.containing_block_size()[0]
        self.flat_tree = []
        for box in self.flatten_tree(linebox):
            new_box = box.copy()
            if isinstance(box, boxes.ParentBox):
                new_box.empty()
            self.flat_tree.append(new_box)
        self.text_fragment = text.TextLineFragment()
        self.execute_formatting()

    @property
    def parents(self):
        for i, box in enumerate(self.flat_tree[:-1]):
            if box.depth < self.flat_tree[i+1].depth:
                yield box

    @property
    def reversed_parents(self):
        for box in reversed(list(self.parents)):
            yield box

    def get_parents_box(self, child):
        child_index = self.flat_tree.index(child)
        depth = child.depth
        for i, box in enumerate(self.reversed_parents):
            if i < child_index:
                if box.depth < depth:
                    depth = box.depth
                    yield box

    def is_a_parent(self, box):
        return box in self.parents

    def is_parent(self, parent, child):
        return parent in self.get_parents_box(child)

    def child_iterator(self):
        for i, box in enumerate(self.flat_tree):
            if not self.is_a_parent(box):
                yield i, box

    def breaking_textbox(self, textbox, allocate_width):
        """
        Cut the long TextBox that sticks out the LineBox only if the TextBox
        can be cut by a line break

        >>> breaking_textbox(textbox, allocate_width)
        (first_element, second_element)

        Eg.
            TextBox('This is a long long long long text')

        is turned into

            (
                TextBox('This is a long long'),
                TextBox(' long long text')
            )

        but
            TextBox('Thisisalonglonglonglongtext')

        is turned into

            (
                TextBox('Thisisalonglonglonglongtext'),
                None
            )

        and

            TextBox('Thisisalonglonglonglong Thisisalonglonglonglong')

        is turned into

            (
                TextBox('Thisisalonglonglonglong'),
                TextBox(' Thisisalonglonglonglong')
            )
        """
        self.text_fragment.set_width(allocate_width)
        # Set css style in TextLineFragment
        self.text_fragment.set_textbox(textbox)
        # We create a new TextBox with the first part of the cutting text
        first_tb = textbox.copy()
        first_tb.text = self.text_fragment.get_text()
        # And we check the remaining text
        if self.text_fragment.get_remaining_text() == "":
            return (first_tb, None)
        else:
            second_tb = textbox.copy()
            second_tb.text = self.text_fragment.get_remaining_text()
            return (first_tb, second_tb)


    def compute_textbox_width(self, textbox):
        """Add the width and height in the textbox attributes and width."""
        self.text_fragment.set_width(-1)
        self.text_fragment.set_textbox(textbox)
        textbox.width, textbox.height = self.text_fragment.get_size()
        return textbox.width


    def execute_formatting(self):
        """
        Eg.

        LineBox[
            InlineBox[
                TextBox('Hello.'),
            ],
            InlineBox[
                InlineBox[TextBox('Word :D')],
                TextBox('This is a long long long text'),
            ]
        ]

        is turned into

        [
            LineBox[
                InlineBox[
                    TextBox('Hello.'),
                ],
                InlineBox[
                    InlineBox[TextBox('Word :D')],
                    TextBox('This is a long'),
                ]
            ], LineBox[
                InlineBox[
                    TextBox(' long long text'),
                ]
            ]
        ]
        """
        width = self.width
        any_element_in_line = True
        for index, child in self.child_iterator():
            #- self.compute_parent_width(child)
            child_width = self.compute_textbox_width(child)
            if child_width <= width:
                width -= child_width
                any_element_in_line = False
            else:
                parents = list(self.get_parents_box(child))
                self.flat_tree.pop(index)
                first_child, second_child = self.breaking_textbox(child, width)
                if second_child is None:
                    # it means we can't cut the child element
                    # We check if it will be the only element in the line
                    if any_element_in_line:
                        # Then we add the element and force the line break
                        for parent in parents:
                            self.flat_tree.insert(index, parent)
                        self.flat_tree.insert(index, first_child)
                    else:
                        self.flat_tree.insert(index, first_child)
                        for parent in parents:
                            self.flat_tree.insert(index, parent)
                else:
                    if self.compute_textbox_width(first_child) <= width:
                        self.flat_tree.insert(index, second_child)
                        for parent in parents:
                            self.flat_tree.insert(index, parent)
                        self.flat_tree.insert(index, first_child)
                    else:
                        self.flat_tree.insert(index, second_child)
                        self.flat_tree.insert(index, first_child)
                        for parent in parents:
                            self.flat_tree.insert(index, parent)
                any_element_in_line = True
                width = self.width

    @property
    def lineboxes(self):
        """
        Build real tree from flat tree
        Eg.
        [
            LineBox with depth=0,
            TextBox("Lorem")  with depth=1,
            InlineBox with depth=1,
            TextBox(" Ipsum ") with depth=2,
            InlineBox with depth=2,
            TextBox("is") with depth=3,
            LineBox with depth=0,
            InlineBox with depth=1,
            InlineBox with depth=2,
            TextBox("very") with depth=3,
            TextBox(" simply") with depth=2,
        ]

        is turned into

        [
            LineBox [
                TextBox("Lorem"),
                InlineBox [
                    TextBox(" Ipsum "),
                    InlineBox [
                        TextBox("is ")
            ], LineBox [
                InlineBox [,
                    InlineBox [
                        TextBox("very")
                    ]
                    TextBox(" simply")
                ]
            ]
        ]
        """
        def build_tree(flat_tree):
            while flat_tree:
                box = flat_tree.pop(0)
                children = list(get_children(box.depth, flat_tree))
                if children:
                    box.children = list(build_tree(children))
                    yield box
                else:
                    yield box

        def get_children(level, flat_tree):
                while flat_tree:
                    box = flat_tree.pop(0).copy()
                    if box.depth > level:
                        yield box
                    else:
                        flat_tree.insert(0, box)
                        break

        tree = list(self.flat_tree)
        while tree:
            line = tree.pop(0)
            level = line.depth
            children = list(get_children(level, tree))
            line.children = list(build_tree(children))
            lines.append(line)
        1/0

    def flatten_tree(self, box, depth=0):
        """
        Return all children in a flat tree (list)
        Eg.

        LineBox [
            TextBox("Lorem"),
            InlineBox [
                TextBox(" Ipsum "),
                InlineBox [
                    TextBox("is very")
                ]
                TextBox(" simply")
            ]
            InlineBox [
                TextBox("dummy")
            ]
            TextBox("text of the printing and.")
        ]

        is turned into

        [
            LineBox with depth=0,
            TextBox("Lorem")  with depth=1,
            InlineBox with depth=1,
            TextBox(" Ipsum ") with depth=2,
            InlineBox with depth=2,
            TextBox("is very") with depth=3,
            TextBox(" simply") with depth=2,
            InlineBox with depth=1,
            TextBox("dummy") with depth=2,
            TextBox("text of the printing and.") with depth=1
         ]
        """
        box.depth = depth
        yield box
        depth+=1
        for child in box.children:
            if isinstance(child, boxes.InlineBox):
                for child in self.flatten_tree(child, depth):
                    yield child
            elif isinstance(child, boxes.TextBox):
                child.depth = depth
                yield child
            elif isinstance(child, boxes.InlineBlockBox):
                raise NotImplementedError
            elif isinstance(child, boxes.InlineLevelReplacedBox):
                raise NotImplementedError
