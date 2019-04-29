import itertools

from octa import (
    Service,
    provides
)


__author__ = 'shawn'


class UuidGenerator(Service):
    """Simple service that emits UUIDs."""
    def __init__(self, prefix='ID', start=1, width=10):
        super(UuidGenerator, self).__init__()
        self.prefix = prefix
        self.counter = itertools.count(start=start)
        self.template = '{0}{1:0%dd}' % width

    @provides
    def get_next_unique_id(self):
        return self.template.format(self.prefix, self.counter.next())
