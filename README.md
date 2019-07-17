# Gasofo (framework for Qwil's hexagonal code architecture)

Gasofo is Qwil's take on a implementing a Hexagonal code architecture
([1](https://marcus-biel.com/hexagonal-architecture/), 
[2](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html), 
[3](https://martinfowler.com/bliki/PresentationDomainDataLayering.html),
[4](https://engineering.laterooms.com/hexagonal-architecture-in-practice/)). 


See `./example` for an example of how gasofo can be used to build up an app.

## Installing Gasofo


`pip install gasofo`


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

Here we defined the service `MyService` with a couple of Needs ports and a single Provides port named 
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

_**Notes on code navigation in PyCharm:** The usual 'Find Usages' and 'Go To Declaration' features would work as usual
but this will only allow you to jump between the deps usage and the stubs methods in the NeedsInterface class. The 
provider implementation is not statically associated hence not discoverable by PyCharm. The easiest way to locate a
matching provider port would be to use the 'Go to Symbol' feature (Navigate > Symbol) will find all definitions of a 
symbol. We recommended creating a custom keymap shortcut for this -- I use super+mouse right click which allows me to 
quicky click on any deps or needs stub and locate other definitions.'_

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

`Autoprovide` allows a convenient way to publish all Provides ports that matches the given regex pattern. If a pattern
is not provided, **all** provides ports of internal services are exposed. Please use this sparingly, and always 
double-check that you are not exposing more than intended by querying `MyDomain.get_provides()`.


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

It was mentioned above that, on instantiation, domains will automatically instantiate all underlying services and 
auto-wire them based on port names. You can use `gasofo.auto_wire()` to do the same for components you instantiate 
yourself using. This would typically be how you'd wire up a full application.

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

# creates provider which provides "get_md5_hash"
md5_provider = func_as_provider(func=hashlib.md5, port='get_md5_hash')  
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
        
serialisation_provider = object_as_provider(provider=Serializers, ports=[
    'serialise_to_json', 
    'serialise_to_xml',
])
```


## Adapters

Adapters allows us to inject logic between a port and the provider of that dependency. One way to look at it is that
services should focus on business logic and accesses a port to get data or perform some action. It should not 
concern itself with how that dependency is provided or what the structure is at the origin, and instead leave it up to
adapters to handle the more mechanical operations like transport, serialisation/deserialisation, payload transformation, etc.

Take for instance a service that provides a certain dataset, and several other services that need that dataset but in 
different formats. Instead of having multiple providers ports for the different formats, we could have all consumers
connect to the same provider but each with a different adapter to handle reformatting.

Another example would be when moving a service to a different process - we could simply introduce adapters that make 
REST or gRPC calls to connections that now span processes with zero changes to the services themselves.

In Qwil we use two kinds of adapters:
1. Service-based adapters
2. Injected adapters


### Service-based adapters

Service based adapters are essentially standard providers i.e. objects that expose INeed and IProvide interfaces. They 
are technically no different from Services except that they contain no business login and instead server as a bridge
between two ports.

By ensuring that we use globally unique port names throughout the application, and guaranteeing that ports with matching
names are compatible, we can simply throw in service-based adapters with the corresponding names to handle 
incompatibilities and let the auto-wiring process hook them up.

For example, say Service A providers port X and this data is needed by service B and C. However, service C needs the
data in a slightly different format. Instead of C declaring a need for X and then pollute its business logic with data
transformation, it should declare the needs with an different port name and rely on an adapter to do the reformatting.

```
    +---------+                    
    |         |
    |    B    X -------------------------------+                                        
    |         |                                |      +---------+
    +---------+                                |      |         |
                                               +----> X    A    | 
                                               |      |         |
    +---------+          +---------------+     |      +---------+
    |         |          |               |     |
    |    C    Xy -----> Xy   MyAdapter   X ----+
    |         |          |               |
    +---------+          +---------------+  

```

### Injected adapters

(NOT YET IMPLEMENTED)

Injected adapters are call-through callables that are injected when a ports are being connected. This will be done 
at wiring time.


Injection can be targetted (i.e. inject between connections for specific ports) or app-wide (injected in all 
connections). The latter will be used mainly in a debug/dev scenario for instrumenting port calls e.g. for real-time
sequence diagrams, performance analysis, detailed logging.

# Visualisation

Visualisation is important as it will allow us to reason about the application and higher levels of abstraction, and
to visually confirm that components are indeed wired the way we intended.

(NOT YET IMPLEMENTED)

* Domain visualisation (no need to instantiate services/domains)
* App visualisation (Domains/Services are instantiated and wired up)
* Real-time sequence diagrams


## Testing 

When done correctly, apps and components written with Gasofo are very suited to the the 
[Arrange-Act-Assert](http://wiki.c2.com/?ArrangeActAssert) / 
[Given-When-Then](https://martinfowler.com/bliki/GivenWhenThen.html) style of 
testing - since the components are stateless the "Givens" can be defined by simply setting up the Needs ports and the 
"Whens" are calls to Provides ports.

We should never need to `mock.patch` anything as long as all dependencies are correctly declared as ports rather than
accessed directly from within the service. 

See `./tests/example/` for some examples of how to test components written with gasofo.

### The basics

For each test scenario, we should attach only Needs ports that are explicitly needed by the behaviour under test. All 
other ports should remain unattached to ensure that tests will fail if an unexpected dependency is accessed.

Attaching a port in a test can be done manually, i.e. preparing a provider and assigning it to the service port. For
example, say we have a Clock service defined as:

```python
class Clock(Service):
    deps = Needs(['get_current_time'])

    @provides
    def tick(self):
        dt = self.deps.get_current_time()
        return dt.strftime('%Y-%m-%d %H:%M')
```

We could test this as such:
```python
class ClockTest(unittest.TestCase):

    def test_tick_returns_formatted_time(self):
        clock_service = Clock()
        
        # GIVEN the current date time is datetime.datetime(2018, 9, 20, 14, 55)
        datetime_provider = func_as_provider(
            func=lambda: datetime.datetime(2018, 9, 20, 14, 55),
            port='get_current_time'
        )
        clock_service.set_provider('get_current_time', datetime_provider)

        # WHEN tick() is called
        result = clock_service.tick()
        
        # THEN '2018-09-20 14:55' is returned
        self.assertEqual('2018-09-20 14:55', result)
```

This will work and is reasonably clean, but does require quite a bit of boilerplate code. We can simplify this further
by using `gasofo.testing.attach_mock_provider`.

### `gasofo.testing.attach_mock_provider`

This is a handy way for generating a provider which can satisfy one or more ports of a service. Using this helper, 
the test above could be rewritten as:

```python
from gasofo.testing import attach_mock_provider

class ClockTest(unittest.TestCase):
        clock_service = Clock()
        
        # GIVEN the current date time is datetime.datetime(2018, 9, 20, 14, 55)
        attach_mock_provider(consumer=clock_service, ports={
            'get_current_time': datetime.datetime(2018, 9, 20, 14, 55),  # return value when port is called
        })

        # WHEN tick() is called
        result = clock_service.tick()
        
        # THEN '2018-09-20 14:55' is returned
        self.assertEqual('2018-09-20 14:55', result)
```

`attach_mock_provider` generates a provider object which offers ports as defined in the `ports` argument, then attaches 
the consuming component to this provider. Any ports on the consumer that is not defined in the call will remain 
unattached.

`attach_mock_provider` also returns the provider object where all generated mock ports are accessible as attributes on 
this object. These attributes are instances of `mock.Mock` objects which allows us to do more elaborate test setup, e.g.

```python
provider = attach_mock_provider(consumer=some_service, ports=['get_a', 'get_b'])  
provider.get_a.return_value = datetime.datetime(2018, 9, 20, 14, 55)  # can set .return_value as usual
provider.get_b.side_effect = {'a':1, 'b'=2}.get   # get_b(x) calls {'a':1, 'b'=2}.get(x)

some_service.do_blah()

provider.get_b.assert_called_once_with(2)  # can be treated like any a standard mock.Mock object
```

Note that the `ports` argument above is declared as a list instead of a dict. This does the same thing except that the
`return_value` of the mock is not set by default.

An extra benefit to using `attach_mock_provider` is that if the component Needs are defined as a `NeedsInterface` 
instance, then the underling mock objects for the ports are created using `mock.create_autospec`. This will assert that 
all calls to it abide by the argspec of the needs port, thereby validating that service methods are accessing deps
as expected. _(The only thing missing for now to complete this picture is wiring-time assertion that connected needs and 
provides port have compatible argspecs)_.

### Given-When-Then

To write even more succinct tests, one can also use the `GasofoTestCase` base class wraps away most of the test setup
and provides the ability to construct tests as a series of GIVEN-WHEN-THEN calls.

For example, to test the `Clock` service defined above
```python
from gasofo.testing import GasofoTestCase

class ClockTest(GasofoTestCase):
    SERVICE_CLASS = Clock  # service under test

    def test_tick_returns_formatted_time(self):
        self.GIVEN(needs_port='get_current_time', returns=datetime.datetime(2018, 9, 20, 14, 55))
        self.WHEN(port_called='tick')  # this also takes kwargs which will all be passed to the port call
        self.THEN(expected_output='2018-09-20 14:55')
```

It is worth noting that the `self.GIVEN` call returns the created mock object while the `self.WHEN` call returns the 
actual output of the port call.

Do also explore the other arguments support by `self.GIVEN` and `self.THEN` as they provide means for declaring more
complex requirements, e.g. setting up side effects for GIVENs or specifying that we do not care about the order of the 
expected output.

`GasofoTestCase` also provides assertions methods to assert that the needs ports are called as expected. This can be a
simple assertion, or a more involved assertion that the dictates the order in which the needs ports must be 
called. For example:

```python
# example taken from tests/example/domains/coffee_orders/test_orders_service.py

self.assert_ports_called(calls=[
    GasofoTestCase.PortCalled(port='db_get_active_order', kwargs={'room': 'Le trou des chouettes'}),
    GasofoTestCase.PortCalled(port='is_valid_menu_item', kwargs={'item_name': 'Flat White'}),
    GasofoTestCase.PortCalled(port='db_add_order_item', kwargs={
        'room': 'Le trou des chouettes',
        'item': 'Flat White',
        'recipient': 'Shawn',
    }),
])
```

For more examples, see `tests/example/domains/coffee_orders/test_order_history_service.py`. Both the tests classes 
defined in this file -- `OrderHistoryServiceTestSimplified` and `OrderHistoryServiceTestWithoutFramework` -- are 
equivalent but with the latter implemented without `GasofoTestCase`.


###  Higher level testing i.e. domains, app, integration, acceptance testing

Writing tests for domains is identical to testing services since they all implement the same interfaces. 

Testing at the app level, as well as integration/acceptance testing can also be expressed in similar forms except that
the setup for the tests would be more elaborate. For example, one might wire up the full application without the edge
dependencies, then treat the whole mesh as a single domain. We could then use the same tooling as described above to 
implement our acceptance tests or integration tests.

See `/Users/shawn/work/gasofo/tests/example/domains/test_app.py` for a simple example of how this might be achieved.
