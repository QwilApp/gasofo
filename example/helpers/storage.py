from gasofo import func_as_provider


class DictStore(object):
    def __init__(self):
        self.store = {}

    def get_store(self):
        return self.store

    @classmethod
    def as_provider(cls, port_name):
        store = cls()
        return func_as_provider(func=store.get_store, port=port_name)
