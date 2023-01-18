# News in rouver 2.5.0

- Drop support for Python 3.7 and 3.8.
- `test_wsgi_app()`: A stream with a `close()` method is now closed.

# News in rouver 2.4.4

## Improvements

- Change the return type of `StartResponseReturnType` to `None` to be more
  flexible and match the definition in typeshed and Python 3.11+.

# News in rouver 2.4.3

## Bug Fixes

- Add `typing-extensions` to dependency list.

# News in rouver 2.4.2

## Improvements

- Template handlers are now guaranteed to be called with a `tuple` for
  previous path arguments. Previously, only a `Sequence` was guaranteed,
  and a mutable `list` was used.

# News in rouver 2.4.1

## Improvements

- Don't call sub-routers inside an exception handler. This improves
  confusing tracebacks when exceptions are raised from a sub-router.

# News in rouver 2.4.0

## Improvements

- Python 3.10 is now officially supported.
- `rouver.test`: `TestRequest` now sets the `REMOTE_ADDR` environment
  variable by default.

# News in rouver 2.3.0

## Improvements

- `rouver.test`: `test_wsgi_arguments()` now accepts all multiplicities.

# News in rouver 2.2.2

## Bug Fixes

- Import ABCs from `collections.abc` instead of `collections`. Fixes
  a `DeprecationWarning`.

# News in rouver 2.2.1

## Improvements

- `rouver.test`: Use build-in `assert` statements instead of assertions
  from the `asserts` package.

# News in rouver 2.2.0

## API Additions

- Sub-routers now have access to WSGI environment variable
  called `rouver.original_path_info` that contains the original
  `PATH_INFO` value.

# News in rouver 2.1.0

## API Additions

- `rouver.args`: Add `"file-or-str"` argument value type.

## Improvements

- `rouver.args`: Use `Literal`s for `ArgumentValueType`.

# News in rouver 2.0.0

## Incompatible Changes

- Drop support for Python 3.5 and 3.6.
- Rework `TestRequest` argument handling.
  - Remove `TestRequest.prepare_for_arguments()`.
  - `TestRequest.content_type` will not be set when calling
    `add_argument()`.
- `ArgumentParser` and `parse_args()` will not raise a
  `BadRequest` if request has wrong content type. Instead,
  they will treat it as if no arguments were given.

## API Additions

- Add `TestRequest.add_file_argument()`.

# News in rouver 1.1.0

## API Additions

- Add `absolute_url()` utility function.

## Improvements

- URL constructing functions, such as `created_as_json()` now encode
  special characters in the path instead of throwing a `ValueError`.

# News in rouver 1.0.0

## Bug Fixes

- `rouver.router`: Include extra headers from `HTTPException` sub-classes
  in responses.

# News in rouver 0.99.2

## API Additions

- `rouver.test`: Add pytest-friendly aliases:
  - `run_wsgi_test()` for `test_wsgi_app()`
  - `FakeRequest` for `TestRequest`
  - `FakeResponse` for `TestResponse`

# News in rouver 0.99.1

## Bug Fixes

- `rouver.test`: Include `Content-Length` header when sending CGI
  arguments in request body (content type `application/x-www-form-urlencoded`).

# News in rouver 0.99.0

## Incompatible Changes

- `parse_args()` is now implemented using werkzeug. While this does not
  change rouver's API, it may have incompatible side-effects or change the
  way CGI arguments are parsed slightly.
- Remove `CGIFileArgument`.

## API Additions

- `rouver.args`: Add `exhaustive` keyword-only argument to `parse_args()`,
  `ArgumentParser.parse_args()`, and `RouteHandlerBase.parse_args()`.

# News in rouver 0.10.9

## Bug Fixes

- Import ABCs from `collections.abc` instead of `collections`. Fixes
  a `DeprecationWarning`.

# News in rouver 0.10.8

## Bug Fixes

- Handle escaped URLs correctly.
- Path arguments are now decoded before being passed to the template handler.
  <

# News in rouver 0.10.7

## API Additions

- `rouver.test`: Add `TestRequest.prepare_for_arguments()`.

# News in rouver 0.10.6

## Improvements

- `rouver.test`: Include `CONTENT_LENGTH` in WSGI environment if body
  is set.

# News in rouver 0.10.5

## API Additions

- `rouver.test`: Add `TestRequest.body`.
- `rouver.test`: Add `TestRequest.set_json_body()`.

# News in rouver 0.10.4

## API Additions

- `rouver.test`: Add `TestResponse.parse_json_body()`.
- `rouver.test`: `TestResponse.assert_content_type()` now accepts a
  list of character sets.

# News in rouver 0.10.3

## API Additions

- `rouver.test`: Add `TestResponse.assert_set_cookie()`.

# News in rouver 0.10.2

## Bug Fixes

- `rouver.test`: `assert_temporary_redirect()` et al. now work
  correctly with query strings and fragments.

# News in rouver 0.10.1

## API Additions

- `rouver.test`: Add `TestRequest.set_env_var()` and
  `TestRequest.set_header()`.
- `rouver.test`: Add `TestResponse.assert_header_not_set()`,
  `assert_content_type()`, `assert_see_other()`, and
  `assert_temporary_redirect()`.

# News in rouver 0.10.0

## API Additions

- `rouver.test`: New WSGI testing module.
- `rouver.response`: `created_at()`, `created_as_json()`,
  `temporary_redirect()`, and `see_also()` now take an optional
  `extra_headers` argument.

## Improvements

- `rouver.types`: Replace `StartResponse`'s argument types with `...`
  `start_response()` takes either two or three arguments. This can not
  be modelled using type hints.

# News in rouver 0.9.0

## API-Incompatible Changes

- `rouver.response`: `created_at()`, `created_as_json()`,
  `temporary_redirect()`, and `see_other()` now treat URLs without a
  leading slash as relative to the request path.

## Improvements

- `rouver.html`: Replace `&mdash;` with `&#x2014;` for improved
  compatibility with XML parsers.
- `rouver.response`: `created_at()`, `created_as_json()`,
  `temporary_redirect()`, and `see_other()` now support absolute URLs.

# News in rouver 0.8.4

Add `py.typed` file to package `rouver` to enable type checking.

# News in rouver 0.8.3

## API Additions

- `rouver.handler`: Add `content_type` argument to
  `RouteHandlerBase.respond()`.

# News in rouver 0.8.2

## API Additions

- `rouver.response`: Add `content_type` argument to `respond()`.

## Bug Fixes

- `rouver.args`: Raise `BadRequest` when a PATCH request has a wrong
  content type.

# News in rouver 0.8.1

## Bug Fixes

- Fix sub-routers with non-ASCII paths.

# News in rouver 0.8.0

This release includes improvements against HTML injection attacks.

## API-Incompatible Changes

- `rouver.html`: `http_status_page()`: The `message` argument will now
  be HTML-escaped. Instead, an `html_message` argument was added.
  `content` was renamed to `html_content`.

## Bug Fixes

- `rouver.html`: Harden all functions against malicious input.
- `rouver.router`: Correctly HTML-escape error messages.

# News in rouver 0.7.0

## API-Incompatible Changes

- `rouver.response`: The following functions now only accept already
  URL-encoded partial URLs:
  - `created_at()`
  - `created_as_json()`
  - `temporary_redirect()`
  - `see_other()`
    Non-ASCII URLs with raise a `ValueError`.
- `rouver.handler`: See above.

# News in rouver 0.6.1

## Bug Fixes

- `rouver.response`: Partial URLs in `temporary_redirect()` etc. were
  URL-encoded by accident.

# News in rouver 0.6.0

## API-Incompatible Changes

- `rouver.handler`: `RouteHandlerBase.respond`: `extra_headers` is now a
  keyword-only argument.

## API Additions

- `rouver.handler`: `RouteHandlerBase.respond`: Add `status` argument.

# News in rouver 0.5.5

## Bug Fixes

- `rouver.args`: `parse_args()` will now work for all methods, even if
  no arguments are supplied.

# News in rouver 0.5.4

## Bug Fixes

- `rouver.handler`: `RouteHandlerBase.parse_args()` can now be called
  inside `prepare_response()`.

# News in rouver 0.5.3

## API Additions

- `rouver.args`: Add `ArgumentParser`.

## Improvements

- `rouver.handler`: `RouteHandlerBase.parse_args()` can now be called
  multiple times.

# News in rouver 0.5.2

## API Additions

- `rouver.handler`: Add `RouteHandlerBase.parse_json_request()`.
- `rouver.handler`: Add `RouteHandlerBase.respond_with_content()`.
- `rouver.response`: Add `respond_with_content()`.

## Improvements

- Include Content-Length header in JSON and HTML responses.

## Bug Fixes

- Use first matching route handler, instead of crashing when multiple routes
  match.

# News in rouver 0.5.1

## Bug Fixes

- `rouver.router`: Ignore trailing slashes.

# News in rouver 0.5.0

## API-Incompatible Changes

- `rouver.handler`: RouteHandlerBase is now an ordinary WSGI application.
  It takes an WSGI environment and a start response handler as constructor
  arguments.
- `rouver.handler`: Redesign RouteHandlerBase API. Implementations must now
  implement `prepare_response()` instead of `__iter__()`.
- `rouver.handler`: All response methods now return an iterable instead
  of an iterator.
- `rouver.handler`: `RouteHandlerBase.path_args` is now acquired from the
  WSGI environment and will not contain the wildcard path.
- `rouver.response`: All response functions now return an iterable instead
  of an iterator.
- `rouver.router`: `add_routes()` now requires a regular WSGI
  application instead of a route handler.
- `rouver.types`: Remove `RouteHandler`. `RouteDescription` now expects
  an `WSGIApplication` in the third field.

## API Additions

- `rouver.handler`: Add `RouterHandlerBase.wildcard_path`.
- `rouver.router`: Add a field `rouver.path_args` to the WSGI environment
  that contains the path arguments formerly passed to route handlers as the
  second argument. The wildcard path is not added to this field.
- `rouver.router`: Add a field `rouver.wildcard_path` to the WSGI
  environment that contains the wildcard path or the empty string.

# News in rouver 0.4.5

## API Additions

- `rouver.router`: Support sub-routers.

# News in rouver 0.4.4

## API Additions

- `rouver.router`: Support wildcard paths.

# News in rouver 0.4.3

## Bug Fixes

- `rouver.response`: Quote non-UTF-8 URLs correctly in Location headers.

# News in rouver 0.4.2

## API Additions

- `rouver.handler`: Add `RouteHandlerBase.temporary_redirect()` and
  `created_as_json()`.
- `rouver.html`: Add `temporary_redirect_page()`.
- `rouver.response`: Add `temporary_redirect` and `created_as_json()`.

## Bug Fixes

- `rouver.router`: Fix nested <p> element in error pages.

# News in rouver 0.4.1

## Bug Fixes

- `rouvers.args`: `parse_args()` will now throw a `BadRequest` if
  the Content-Type is incorrect for POST and PUT requests.

# News in rouver 0.4.0

## API-Incompatible Changes

- `rouver.types`: Rename `HeaderType` to `Header`.
- `rouver.types`: Rename `EnvironmentType` to `WSGIEnvironment`.
- `rouver.types`: Rename `StartResponseType` to `StartResponse`.
- `rouver.types`: Rename `RouteType` to `RouteDescription`.

## API Additions

- `rouver.types`: Add `WSGIApplication` and `WSGIResponse`.

# News in rouver 0.3.1

## Improvements

- Type hinting: Use `Sequence` over `List` and `Mapping` over `Dict` in
  function/method arguments.

## Bug Fixes

- `rouver.html`: Fix argument types of `bad_arguments_page()` and
  `bad_arguments_list()`.

# News in rouver 0.3.0

## API-Incompatible Changes

- `rouver.html`: `http_status_page()`: `message` argument is now an
  optional, keyword-only argument.
- `rouver.router`: Template handlers must now be installed before calling
  `add_routes()`.

## API Additions

- `rouver.html`: `http_status_page()`: Add new optional argument
  `content`.
- `rouver.html`: Add `bad_arguments_list()`.
- `rouver.types`: Add `BadArgumentsDict`.

## Improvements

- `rouver.router`: Router now returns a custom error page when
  `ArgumentsError` is raised.

# News in rouver 0.2.1

## Bug Fixes

- `rouver.handler`: Derive `RouteHandlerBase` from `Iterable`.
- `rouver.response`/`rouver.handler`: Fix return types of response methods.

# News in rouver 0.2.0

## API Additions

- `rouver.handler`: Add `RouteHandlerBase`.
- `rouver.html`: Add `created_at_page()`.
- `rouver.response`: Add `respond_ok()`, `respond_with_json()`, and
  `created_at()`.

# News in rouver 0.1.1

## Improvements

- `rouver.response`: Responses now return an iterator so they can be used as
  return values from `__iter__()` methods.

# News in rouver 0.1.0

## API Additions

- `rouver.args`: Add `parse_args()`, `Multiplicity`, `FileArgument`,
  and `CGIFileArgument`.
- `rouver.exceptions`: Add `ArgumentsError`.
- `rouver.html`: Add `http_status_page()` and `see_other_page()`.
- `rouver.status`: Add `status_line()`.
- `rouver.response`: Add `respond_with_html()` and `see_other()`.
- `rouver.router`: Add `Router`.
- `rouver.types`: Add `EnvironmentType`, `HeaderType`,
  `StartResponseReturnType`, `StartResponseType`, `RouterHandler`,
  `RouterType`, and `RouteTemplateHandler`.
