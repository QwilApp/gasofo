import logging
import site
import os


logging.basicConfig(level=logging.DEBUG)


def get_parent_dir():
    my_dir = os.path.dirname(__file__)
    return os.path.abspath('./{}/../'.format(my_dir))


def add_project_root_as_site_package_dir():
    site.addsitedir(get_parent_dir())


if __name__ == '__main__':
    add_project_root_as_site_package_dir()

    from example.domains.coffee_orders import CoffeeOrderDomain
    print ''
    print CoffeeOrderDomain
    print "NEEDS:", CoffeeOrderDomain.get_needs()
    print "PROVIDES", CoffeeOrderDomain.get_provides()
