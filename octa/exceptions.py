class PortDefinitionError(SyntaxError):
    """Raised when port definition or usage does not meet constraints."""


class ServiceDefinitionError(SyntaxError):
    """Raised when Service definition does not meet constraints."""


class DomainDefinitionError(SyntaxError):
    """Raised when Domain definition does not meet constraints."""


class WiringError(Exception):
    """Raised when there are problems with connecting a needs port to a provides port."""


class NotAdapted(Exception):
    """Raised when an unadapted port is called."""
