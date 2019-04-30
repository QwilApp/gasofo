import itertools

from gasofo import object_as_provider

__author__ = 'shawn'


class UuidGenerator(object):
    """Simple object that emits UUIDs."""

    def __init__(self, prefix='ID', start=1, width=10):
        super(UuidGenerator, self).__init__()
        self.prefix = prefix
        self.counter = itertools.count(start=start)
        self.template = '{0}{1:0%dd}' % width

    def get_next_unique_id(self):
        return self.template.format(self.prefix, self.counter.next())

    def as_provider(self):
        """Wrap this object as a provider so it can be wired to Domains/Services."""
        return object_as_provider(provider=self, ports=['get_next_unique_id'])
