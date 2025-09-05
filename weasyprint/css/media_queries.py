"""Handle media queries.

https://www.w3.org/TR/mediaqueries-4/

"""

import tinycss2

from ..logger import LOGGER
from .tokens import remove_whitespace, split_on_comma


MEDIA_TYPES = {
    'all',
    'print',
    'screen'
}

# For now support for only operator
LOGICAL_OPERATORS = {
    'only'
}


def evaluate_media_query(query_list, device_media_type):
    """Return the boolean evaluation of `query_list` for the given
    `device_media_type`.

    :attr query_list: a cssutilts.stlysheets.MediaList
    :attr device_media_type: a media type string (for now)

    """
    # TODO: actual support for media queries, not just media types
    if 'only' in query_list:
        if len(query_list) <= 1:
            LOGGER.warning(
                "Invalid media query: The 'only' keyword was used by itself and must be "
                "followed by a media type (e.g., 'only screen').")
            return False
        if query_list.index('only') != 0:
            LOGGER.warning(
                "Invalid media query: The 'only' keyword must appear at the very beginning.")
            return False
        if query_list[1] not in MEDIA_TYPES:
            LOGGER.warning("Invalid media query: The 'only' keyword must be immediately followed by a "
                "valid media type (like 'screen' or 'print'")
            return False
    return 'all' in query_list or device_media_type in query_list


def parse_media_query(tokens):
    tokens = remove_whitespace(tokens)
    if not tokens:
        return ['all']
    else:
        media = []
        for part in split_on_comma(tokens):
            for token in tokens:
                if token.type == 'ident' and (token.value in MEDIA_TYPES or token.value in LOGICAL_OPERATORS):
                    media.append(token.lower_value)
                else:
                    LOGGER.warning(
                        'Expected a media type or logical operator, got %r', tinycss2.serialize(part))
                    return
        return media
