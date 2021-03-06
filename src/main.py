from werkzeug.exceptions import HTTPException
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.routing import Map, Rule
from werkzeug.serving import run_simple
from werkzeug.wrappers import Request

import db
import views
from settings import MEDIA_ROOT, STATIC_ROOT

url_map = Map([
    Rule('/', endpoint='index'),
    Rule('/cart', endpoint='cart'),
    Rule('/shops/create', endpoint='shop_create'),
    Rule('/shops/<slug>', endpoint='shop_detail'),
    Rule('/shops/<slug>/<category>', endpoint='shop_category'),
    Rule('/shops/<slug>/products/create', endpoint='product_create'),
    Rule('/shops/<slug>/products/<id>', endpoint='product_detail'),
    Rule('/shops/<slug>/products/<id>/update', endpoint='product_update'),
    Rule('/shops/<slug>/products/<id>/delete', endpoint='product_delete'),
    Rule('/shops/<slug>/reviews/create', endpoint='shop_review_create'),
    Rule('/users/create', endpoint='user_create'),
    Rule('/users/login', endpoint='user_login')
])


def dispatch_request(request):
    adapter = url_map.bind_to_environ(request.environ)
    try:
        endpoint, values = adapter.match()
        view_func = getattr(views, endpoint)
        return view_func(request, values)
    except HTTPException as err:
        return err


def application(environ, start_response):
    request = Request(environ)
    response = dispatch_request(request)
    return response(environ, start_response)


application = SharedDataMiddleware(
    application, {'': STATIC_ROOT, '/media': MEDIA_ROOT})

if __name__ == '__main__':
    run_simple('127.0.0.1',
               8000,
               application,
               use_debugger=True,
               use_reloader=True)
