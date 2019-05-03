import types

from gasofo.exceptions import (
    DuplicatePortDefinition,
    NeedsInterfaceDefinitionError,
)
from gasofo.ports import PortArray


class Needs(PortArray):
    """Used to defined the Needs ports of a Service.

        @DynamicAttrs <-- let pycharm know to expect dynamically added attributes
    """

    def __init__(self, ports):
        super(Needs, self).__init__()

        if isinstance(ports, basestring):
            ports = [ports]

        for port in ports:
            try:
                self.add_port(port_name=port)
            except DuplicatePortDefinition:
                raise DuplicatePortDefinition('"{}" port is duplicated'.format(port))


class NeedsInterfaceMetaclass(type):
    """ Metaclass that converts methods to Needs ports."""
    def __new__(mcs, name, bases, state):
        if bases == (Needs,):  # This is the NeedsInterface class itself, not its subclass
            return type.__new__(mcs, name, bases, state)

        needs = {}
        for attr_name, member in state.items():
            if attr_name == '__init__' and bases != (Needs, ):
                msg = '{}.__init__ - cannot override constructor of Needs Interface'.format(name)
                raise NeedsInterfaceDefinitionError(msg)

            if attr_name.startswith('__') and attr_name.endswith('__'):
                continue

            if not isinstance(member, types.FunctionType):
                msg = '{}.{} - only functions are allowed as attributes of a Needs Interface'.format(name, attr_name)
                raise NeedsInterfaceDefinitionError(msg)

            PortArray.assert_valid_port_name(port_name=attr_name)

            # actual functions do not actually make it onto the class as they will be replaced by ports.
            # However, we do keep a reference to the original functions for debugging and testing purposes.
            needs[attr_name] = state.pop(attr_name)

        state['_needs'] = needs.keys()
        state['_needs_template_funcs'] = needs

        # SHC: not sure this is a good ideal. Hide this away for now
        # state['_template_class'] = type(name + 'Template', (), needs)  # generate subclass-able interface class

        return type.__new__(mcs, name, bases, state)


class NeedsInterface(Needs):
    """Used to define Needs ports of a Service as an interface class."""
    __metaclass__ = NeedsInterfaceMetaclass

    def __init__(self):
        super(NeedsInterface, self).__init__(ports=self._needs)  # apply needs discovered by metaclass
