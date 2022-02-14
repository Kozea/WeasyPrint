"""Handle media queries.

https://www.w3.org/TR/mediaqueries-4/

"""

import tinycss2

from ..logger import LOGGER
from .utils import remove_whitespace, split_on_comma


def evaluate_media_query(query_list, device_media_type):
    """Return the boolean evaluation of `query_list` for the given
    `device_media_type`.

    :attr query_list: a cssutilts.stlysheets.MediaList
    :attr device_media_type: a media type string (for now)

    """
    # TODO: actual support for media queries, not just media types
    return 'all' in query_list or device_media_type in query_list


def parse_media_query(tokens):
    tokens = remove_whitespace(tokens)
    if not tokens:
        return ['all']
    else:
        media = []
        for part in split_on_comma(tokens):
            types = [token.type for token in part]
            if types == ['ident']:
                media.append(part[0].lower_value)
            else:
                LOGGER.warning(
                    'Expected a media type, got %r', tinycss2.serialize(part))
                return
        return media
