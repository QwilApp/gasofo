# Gasofo (framework for Qwil's hexagonal code architecture)

(short description of hexa and gasofo)

See `./example` for an example of how gasofo can be used to build up an app.


## Defining Services

...

To cover:
* Constraints: stateless, no constructor
* Provides
    * `@provides`
    * `@provides_with`
    * port name constraints
    * brief mention of flags
    * `cls.get_provides()`
    
* `self.deps`
    * Needs
    * Needs as Interface (recommended)
    * `cls.get_needs()`


## Defining Domains

...

To cover:
* `__services__` and `__provides__`
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
    