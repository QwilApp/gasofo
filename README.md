# Gasofo (framework for Qwil's hexagonal code architecture)

Gasofo is Qwil's take on a implementing a Hexagonal code architecture
([1](https://marcus-biel.com/hexagonal-architecture/), 
[2](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html), 
[3](https://martinfowler.com/bliki/PresentationDomainDataLayering.html),
[4](https://engineering.laterooms.com/hexagonal-architecture-in-practice/)). 


See `./example` for an example of how gasofo can be used to build up an app.

## Installing Gasofo


`pip install git+https://gitlab.tooling-dev.private.qwil.network/open/gasofo@v1.0.0`


## Defining Services

Services should be stateless and should only access resources other services via its "Needs" ports. Functionality 
provided by a service are exposed via "Provides" ports.

A Service can be defined as such:

```python
from gasofo import Service, Needs, provides

class MyService(Service):
    
    deps = Needs(['some_data', 'another_service'])  # ports this service 'Needs'
    
    @provides
    def my_feature(self, x):
        data = self.deps.some_data()  # needs are accessed via self.deps.<port_name>
        more_data = self.another_service(value=x)
        return data + more_data
```

Here we defined a the service `MyService` with a couple of Needs ports and a single Provides port named 
"my_feature". 

Methods on instances of this class can be called just like a regular class, but only the ones tagged 
with `@provides` are discoverable as a port.

Dependencies of the service are access through the Needs port via `self.deps.PORT_NAME(...)`. These ports will be 
injected with actual provider functions when the application is wired up. Calling a port before it is connected to a
provider will raise a `DisconnectedPort` exception.

The ports of a service can be queried by calling `get_needs()` and `get_provides()` on the service class or instance.
This helps with the visualisation and auto-wiring of Services to form business domains and complete applications.


### Validations on declaration

Exceptions will be raised during class construction (which usually means when you import the module) if the following
validations fail:
* Constructors (`__init__`) are not allowed since services are meant to be stateless.
* All `self.deps.<PORT_NAME>` must reference a declared Needs port.
* All declared Needs ports must be reference at least once by any of the methods in the class.
* All port names must start with a lower-case letter and can only contain alphanumeric characters or underscores.
* Port names cannot match one of the reserved names, e.g. `get_needs`, `get_provides`, etc. For a complete list, see
  `gasofo.ports.RESERVED_PORT_NAMES`.


### Declaring Needs ports as interfaces

The example in the sections above declares Needs ports using a list of port names. This is very convenient and quick,
but is not very IDE or testing friendly. 

The recommended approach is to declare Needs ports using `NeedsInterface`.
```python
from gasofo import Service, NeedsInterface, provides


class MyServiceNeeds(NeedsInterface):

    def some_data(self):
        # type: () -> int
        """A brief description."""
        
    def another_service(self, value):
        # type: (int) -> int
        """You can include as much doc here as you like."""
        
        
class MyService(Service):
    
    deps = MyServiceNeeds()
    
    @provides
    def my_feature(self, x):
        data = self.deps.some_data()  # needs are accessed via self.deps.<port_name>
        more_data = self.another_service(value=x)
        return data + more_data
```

Benefits of using `NeedsInterface` over `Needs([...])`:
* Attributes of `self.deps` are no longer dynamically inject, which means that auto-completion and suggestions in IDE
  will now work.
* The method construct allows for type hinting and docstrings.
* The function signature is now explicit and will be used by the testing framework to assert that the ports are called
  with the expected arguments.
  
The type hinting is optional as far as Gasofo is concerned, but we encourage using it. These ports are only wired to 
concrete implementation at run-time, so the type hints is the only reliable way for your IDE infer the type of the
arguments and return values. That extra effort is worth it!

### Using `@provides_with`

When we use `@provides` to define Provides ports, the name of the port will be taken from the method name. In situations
where we want the port names to differ from the actual method name, we can use `@provides_with`.

```python
from gasofo import Service, provides_with

class MyService(Service):

    @provides_with('db_get_blah')
    def get_blah(self, blah_id):
        # ...
```

The mismatch between the published port name and actual method name could cause confusion, so use this sparingly.

`@provides_with` also allows us to attached additional metadata (flags) ports, e.g. 
`@provides_with('db_get_blah', web_only=True)`. 

We do not currently use these flags, so we will hold off on the docs for now :)

## Defining Domains

...

To cover:
* `__services__` and `__provides__`
* `AutoProvide()`
* (to be implemented) argspec of domain methods
* "Nestability"

## Wiring up an application

...

To cover:
* Framework does not stop you from manually connecting ports to any other ports. Project convention (e.g. globally 
  unique port names to denote intent and compatibility) makes it easier to reason about ports and allow for auto-wiring
  of Domains, Services, Adapters, Providers etc into a fully functioning application.
* manual connection
* auto wiring


# Visualisation

(NOT YET IMPLEMENTED)

* Domain visualisation (no need to instantiate services/domains)
* App visualisation (Domains/Services are instantiated and wired up)
* Real-time sequence diagrams

## Implementing Providers


(stuff that don't meet requirements of a Service,  but implements `IProvide`. Edge stuff, e.g. dbs)

* func_as_provider
* object_as_provider

## Adapters

...

To cover:

* Service-based adapters (note usage of globally unique port names to denote compatibilty of interfaces and exposing the 
  need of service-based adapters)  
* (to be implemented) Injected adapters - one that is injected between the connection of a specific port


## Testing 

...

To cover:
* ad-hoc providers
* mock as providers
* (recommended) Test Adapters which does argspec checks for free. 
* 


# Implementation Details

...

To cover:

* Discuss the layers of abstraction:
    1. (lowest level) PortArray
    2. INeed and IProvide interface + wiring
        * Conceptual connectivity vs actual execution hops. (show traceback of a call?)
    3. Service and Domain definition
