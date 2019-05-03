class GasofoError(Exception):
    """Base class for all exceptions raised by Gasofo."""


class DuplicateProviders(GasofoError):
    """Raised when there are multiple providers of the same port."""


class DuplicatePortDefinition(GasofoError):
    """Raised when attempting to create a port that already exists."""


class SelfReferencingMadness(GasofoError):
    """Raised when a component has provides ports that satisfy its own needs."""


class DisconnectedPort(GasofoError):
    """Raised when attempting to access a port that has not been connected or assigned with a provider."""


class WiringError(GasofoError):
    """Raised when there was a problem wiring up ports."""


class UnknownPort(GasofoError):
    """Raised when referencing a port that does not exist."""


class UnusedPort(GasofoError):
    """Raised when service declares deps that are unused."""


class InvalidPortName(GasofoError):
    """Raised when an invalid port name is used."""


class ServiceDefinitionError(GasofoError):
    """Raised when a Service definition is invalid."""


class DomainDefinitionError(GasofoError):
    """Raised when a Service definition is invalid."""


class NeedsInterfaceDefinitionError(GasofoError):
    """Raised when a Needs interface is incorrectly defined."""


class YouCannotDoThat(GasofoError):
    """Raised when an invalid action is requested or executed."""


class IncompatibleProvider(GasofoError):
    """Raised when connecting an incompatible provider to a port."""


class InconsistentInterface(GasofoError):
    """Raised when ports in question have inconsistent interfaces."""
