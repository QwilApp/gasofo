class GasofoError(Exception):
    """Base class for all exceptions raised by Gasofo."""


class DuplicateProviders(GasofoError):
    """Raised when there are multiple providers of the same port."""


class SelfReferencingMadness(GasofoError):
    """Raised when a component has provides ports that satisfy its own needs."""


class DisconnectedPort(GasofoError):
    """Raised when attempting to access a port that has not been connected or assigned with a provider."""


class WiringError(GasofoError):
    """Raised when there was a problem wiring up ports."""


class UnknownPort(GasofoError):
    """Raised when referencing a port that does not exist."""


class InvalidPortName(GasofoError):
    """Raised when an invalid port name is used."""
