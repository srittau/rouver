# Rouver

A microframework for Python 3, based on werkzeug.

[![MIT License](https://img.shields.io/pypi/l/rouver.svg)](https://pypi.python.org/pypi/rouver/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/rouver)](https://pypi.python.org/pypi/rouver/)
[![GitHub](https://img.shields.io/github/release/srittau/rouver/all.svg)](https://github.com/srittau/rouver/releases/)
[![pypi](https://img.shields.io/pypi/v/rouver.svg)](https://pypi.python.org/pypi/rouver/)
[![Travis CI](https://travis-ci.org/srittau/rouver.svg?branch=master)](https://travis-ci.org/srittau/rouver)

## Routing

```python
>>> from rouver.router import Router
>>> from rouver.response import respond_with_html, respond_with_json
>>> def get_index(environ, start_response):
...     return respond_with_html(start_response, "<div>Foo</div>")
>>> def get_count(environ, start_response):
...     return respond_with_json(start_response, {"count": 42})
>>> router = Router()
>>> router.add_routes([
...     ("", "GET", get_index),
...     ("count", "GET", get_count),
... ])

```

Routes with placeholders:

```python
>>> def get_addition(environ, start_response):
...     num1, num2 = path
...     return response_with_json(start_response, {"result": num1 + num2})
>>> def numeric_arg(request, path, value):
...     return int(value)
>>> router.add_template_handler("numeric", numeric_arg)
>>> router.add_routes([
...     ("add/{numeric}/{numeric}", "GET", get_addition),
... ])
```

Routes with wildcards:

```python
>>> def get_wildcard(environ, start_response):
...     # environ["rouver.wildcard_path"] contains the remaining path
...     return respond(start_response)
>>> router.add_routes([
...     ("wild/*", "GET", get_wildcard),
... ])
```

Sub-routers:

```python
>>> def get_sub(environ, start_response):
...     return respond(start_response)
>>> sub_router = Router()
>>> sub_router.add_routes([
...     ("sub", "GET", get_sub),
... ])
>>> router.add_sub_router("parent", sub_router)
```

## Argument Handling

```python
>>> from rouver.args import Multiplicity, parse_args
>>> from rouver.response import respond_with_json
>>> def get_count_with_args(request, path, start_response):
...     args = parse_args(request.environ, [
...         ("count", int, Multiplicity.REQUIRED),
...     ])
...     return respond_with_json({"count": args["count"]})
```

## WSGI Testing

```python
>>> from rouver.test import create_request, test_wsgi_app
>>> request = create_request("GET", "/my/path")
>>> response = test_wsgi_app(app, request)
>>> response.assert_status(HTTPStatus.OK)
```
