import os.path
from attest import Tests


def resource_filename(basename):
    return os.path.join(os.path.dirname(__file__), 'resources', basename)

all = Tests('.'.join((__name__, mod, 'suite'))
            for mod in ('css',
                        'properties'))
