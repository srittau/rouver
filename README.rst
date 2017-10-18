Rouver
======

A microframework for Python 3, based on werkzeug.

.. image:: https://img.shields.io/github/release/srittau/rouver/all.svg
   :target: https://github.com/srittau/rouver/releases/
.. image:: https://travis-ci.org/srittau/rouver.svg?branch=master
   :target: https://travis-ci.org/srittau/rouver

Routing
-------

>>> from rouver.router import Router
>>> from rouver.response import respond_with_html, respond_with_json
>>> def get_index(request, path, start_response):
...     return respond_with_html(start_response, "<div>Foo</div>")
>>> def get_count(request, path, start_response):
...     return respond_with_json(start_response, {"count": 42})
>>> router = Router()
>>> router.add_routes([
...     ("", "GET", get_index),
...     ("count", "GET", get_count),
... ])

Routes with placeholders:

>>> def get_addition(request, path, start_response):
...     num1, num2 = path
...     return response_with_json(start_response, {"result": num1 + num2})
>>> def numeric_arg(request, path, value):
...     return int(value)
>>> router.add_template_handler("numeric", numeric_arg)
>>> router.add_routes([
...     ("add/{numeric}/{numeric}", "GET", get_addition),
... ])

Argument Handling
-----------------

>>> from rouver.args import Multiplicity, parse_args
>>> from rouver.response import respond_with_json
>>> def get_count_with_args(request, path, start_response):
...     args = parse_args(request.environ, [
...         ("count", int, Multiplicity.REQUIRED),
...     ])
...     return respond_with_json({"count": args["count"]})
