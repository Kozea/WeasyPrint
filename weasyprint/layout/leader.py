"""Leaders management."""

from ..formatting_structure import boxes


def leader_index(box):
    """Get the index of the first leader box in ``box``."""
    for i, child in enumerate(box.children):
        if child.is_leader:
            return (i, None), child
        if isinstance(child, boxes.ParentBox):
            child_leader_index, child_leader = leader_index(child)
            if child_leader_index is not None:
                return (i, child_leader_index), child_leader
    return None, None


def handle_leader(context, line, containing_block):
    """Find a leader box in ``line`` and handle its text and its position."""
    index, leader_box = leader_index(line)
    extra_width = 0
    if index is not None and leader_box.children:
        text_box, = leader_box.children

        # Abort if the leader text has no width
        if text_box.width <= 0:
            return

        # Extra width is the additional width taken by the leader box
        extra_width = containing_block.width - sum(
            child.width for child in line.children
            if child.is_in_normal_flow())

        # Take care of excluded shapes
        for shape in context.excluded_shapes:
            if shape.position_y + shape.height > line.position_y:
                extra_width -= shape.width

        # Available width is the width available for the leader box
        available_width = extra_width + text_box.width
        line.width = containing_block.width

        # Add text boxes into the leader box
        number_of_leaders = int(line.width // text_box.width)
        position_x = line.position_x + line.width
        children = []
        for i in range(number_of_leaders):
            position_x -= text_box.width
            if position_x < leader_box.position_x:
                # Don’t add leaders behind the text on the left
                continue
            elif (position_x + text_box.width >
                    leader_box.position_x + available_width):
                # Don’t add leaders behind the text on the right
                continue
            text_box = text_box.copy()
            text_box.position_x = position_x
            children.append(text_box)
        leader_box.children = tuple(children)

        if line.style['direction'] == 'rtl':
            leader_box.translate(dx=-extra_width)

    # Widen leader parent boxes and translate following boxes
    box = line
    while index is not None:
        for child in box.children[index[0] + 1:]:
            if child.is_in_normal_flow():
                if line.style['direction'] == 'ltr':
                    child.translate(dx=extra_width)
                else:
                    child.translate(dx=-extra_width)
        box = box.children[index[0]]
        box.width += extra_width
        index = index[1]
