import logging
import site
import os


__author__ = 'shawn'


logging.basicConfig(level=logging.DEBUG)


def get_parent_dir():
    my_dir = os.path.dirname(__file__)
    return os.path.abspath('./{}/../'.format(my_dir))


def add_project_root_as_site_package_dir():
    site.addsitedir(get_parent_dir())


if __name__ == '__main__':
    add_project_root_as_site_package_dir()

    from example.app import create_app

    app = create_app()
    print 'MENU', app.get_menu_items()
    print app.open_for_orders(requester='Nicolas', room='Qwil')
    print app.make_order(requester='Shawn', room='Qwil', order_item='Flat White')
    print app.make_order(requester='Nicolas', room='Qwil', order_item='Cappucino')
    print app.make_order(requester='Casey', room='Qwil', order_item='Hot Chocolate')
    print app.close_orders(requester='Nicolas', room='Qwil')
