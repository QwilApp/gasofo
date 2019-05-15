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
        more_data = self.deps.another_service(value=x)
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
        more_data = self.deps.another_service(value=x)
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

Domains are a collection of components (services or other domains) grouped together and encapsulated to form a higher 
level business component. A subset of ports from the containing components are published as the Provides ports of the 
domain, and all Needs ports of components that are not fulfilled internally by matching Provides are exposed as the
Needs of the Domain.

```python
from gasofo import Domain
from myproject.services import MyService, AnotherService

class MyDomain(Domain):
    __services__ = [MyService, AnotherService]  # Components contained in this domain
    __provides__ = ['get_blah', 'do_something_else']  # subset of ports from services defined in __services
```

`__services__` should be defined as a list of components (Services or Domains) classes, not instances. An instance of 
each of these components will be instantiated when the Domain is instantiated, and the internal ports that have 
matching names will be automatically wired together.

The Domain class should not contain any other attributes, methods, or a constructor.

As with services, ports of a domain can be queried by calling `get_needs()` and `get_provides()` on the domain class 
or instance.

Upon instantiation, proxy methods are dynamically bound to the domain object so the Provides ports can also be accessed
as a method call i.e. `my_domain_instance.my_port(...)`. This is  handy but is not currently very
IDE friendly -- dynamically added methods and the underlying argspec of the port are not known to IDES so code
suggestion and type checking will not work. (We may address this at some point if we find ourselves needing 
to access these methods on a regular basis.)

### Automatically registering Provides ports for domains

For domains with lots of internal component and lots of intended Provides ports, manually defining them and keeping
them up-to-date can be a chore.

For case like this, use `AutoProvide`:

```python
from gasofo import Domain, AutoProvide
from myproject.services import MyService, AnotherService

class MyDomain(Domain):
    __services__ = [MyService, AnotherService]  # Components contained in this domain
    __provides__ = AutoProvide(pattern='db_.*')  # auto export all ports that start with db_
```

`Autoprovide` allows a convenient way to publish all Provides ports that matches the given regex pattern. If a pattern,
is not provided, **all** ports. Please use this sparingly, and always double-check that you are not exposing more than
intended by querying `MyDomain.get_provides()`.


## Wiring up an application

In the simplest of use cases, one can manually hook up a Needs port by calling 
`service_instance.deps.connect_port(port_name='blah', func=some_callable)`. Note that this is an operation on the
 `service.deps` and is connectable to anything callable. Working at this level can get unwieldy once we have more than 
 a handful of ports in an application.
 
It is therefore recommended that the wiring up if ports is done at a higher level, i.e. at the component level. For
example:

```python
c1 = MyComponent()  # This could be a Service or Domain 
c2 = MyProvider()  # Anything that implements IProvide, e.g. Service, Domain, or some custom implementation

c1.set_provider(port_name='blah', provider=c2)  # c1.deps.blah  ---> c2.blah
```

The pre-requisite here is that the provider's port name has to match the port name of the consumer. This we believe is 
a good thing -- having globally unique port names within the application to denote intent and compatibility makes it
easier to reason about ports and allow for auto-wiring.

### Auto-wiring

Speaking of auto-wiring, we mentioned about that on instantiation domains would automatically instantiate all
underlying services and auto-wire them based on port names. You can also do the same for a components you instantiate
yourself using `gasofo.auto_wire()`. This would typically be how you'd wire up a full application.

```python
from gasofo import auto_wire, Domain
from myapp.domains import *
from myapp.adapters import *

class MyAwesomeApp(Domain):  # encapsulate all my app domain into a single domain
    __services__ = [DomainA, DomainB, DomainC, DomainD]
    __provides__ = LIST_OF_PORTS_TO_EXPOSE_AT_APP_LEVEL
    
def get_app():
    app = MyAwesomeApp()
    dependencies = [
        my_db_provider(),
        redis_provider(),
        logging_provider(),
    ]
    
    auto_wire([app] + dependencies, expect_all_ports_connected=True)  # raise if there are unfulfilled ports
    return app
``` 

### Convenience functions for creating providers

As mentioned above, the recommended approach to wiring is to do so at the component level. This means that any callable
we wish to include in the wiring needs to implement the `gasofo.IProvide` interface.

This isn't hard to do, but involves unnecessary boiler plate to wrap them up in a compatible class structure.

For cases like this, you can use `object_as_provider` or `func_as_provider` to automatically wrap an object or function
within a wrapper that exposes the `IProvide` interface.

Some examples:

```python
from gasofo import func_as_provider
import hashlib

md5_provider = func_as_provider(func=hashlib.md5, port='get_md5_hash')  # creates provider which provides "get_md5_hash"
```

```python
from gasofo import object_as_provider

class MyStack(object):
    def __init__(self):
        self.stack = []
        
    def push_to_stack(self, value):
        self.stack.append(value)
        
    def pop_from_stack(self):
        return self.stack.pop()
        
stack_provider = object_as_provider(provider=MyStack(), ports=['push_to_stack', 'pop_from_stack'])
```

```python
from gasofo import object_as_provider

# we can also expose class methods and static methods as ports
class Serializers(object):
    
    @classmethod 
    def serialise_to_json(cls, payload):
        # ...
        
    @staticmethod
    def serialise_to_xml(payload):
        # ...
        
 serialisation_provider = object_as_provider(provider=Serializers, ports=['serialise_to_json', 'serialise_to_xml'])
```

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
