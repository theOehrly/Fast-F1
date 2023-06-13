# copied and adapted from https://github.com/Rapptz/discord.py/pull/6863

import logging
import re

from sphinx.application import Sphinx
from sphinx.util import logging as sphinx_logging


class NitpickIgnoreFiles(logging.Filter):

    def __init__(self, app: Sphinx) -> None:
        self.app = app
        super().__init__()

    def filter(self, record: sphinx_logging.SphinxLogRecord) -> bool:
        if getattr(record, 'type', None) == 'ref':
            for pattern in self.app.config.nitpick_ignore_files:
                if re.match(pattern, record.location.get('refdoc')):
                    return False
            return True

        return True


def setup(app: Sphinx):
    app.add_config_value('nitpick_ignore_files', [], '')
    f = NitpickIgnoreFiles(app)
    sphinx_logging \
        .getLogger('sphinx.transforms.post_transforms') \
        .logger.addFilter(f)
