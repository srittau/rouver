# Changelog

## [Unreleased] –

### Added

- Add support for Python 3.12 through 3.14.

### Removed

- Remove support for Python 3.9 and earlier.

## [2.6.3]

### Added

- Declare compability with werkzeug 3.

## [2.6.2]

### Fixed

- Improve RFC 5987 compatibility in `rouver.test`. This also makes rouver
  work with Werkzeug 2.3.

## [2.6.1]

### Fixed

- Fix `SCRIPT_NAME` in sub routers to include the parent router paths.

## [2.6.0]

### Added

- `TestRequest`: Add script name handling:
    - Add field `script_name`.
    - Add read-only property `full_path`.
    - Include `SCRIPT_NAME` item in WSGI dictionary.

## [2.5.1]

### Fixed

- `RouteHandlerBase`: If a closable stream is returned from
  `prepare_response()`, it will be closed after the response has been sent.

## [2.5.0]

### Removed

- Drop support for Python 3.7 and 3.8.

### Changed

- `test_wsgi_app()`: A stream with a `close()` method is now closed.

## [2.4.4]

### Changed

- Change the return type of `StartResponseReturnType` to `None` to be more
  flexible and match the definition in typeshed and Python 3.11+.

## [2.4.3]

### Fixed

- Add `typing-extensions` to dependency list.

## [2.4.2]

### Changed

- Template handlers are now guaranteed to be called with a `tuple` for
  previous path arguments. Previously, only a `Sequence` was guaranteed,
  and a mutable `list` was used.

## [2.4.1]

### Changed

- Don't call sub-routers inside an exception handler. This improves
  confusing tracebacks when exceptions are raised from a sub-router.

## [2.4.0]

### Added

- Python 3.10 is now officially supported.
- `rouver.test`: `TestRequest` now sets the `REMOTE_ADDR` environment
  variable by default.

## [2.3.0]

### Added

- `rouver.test`: `test_wsgi_arguments()` now accepts all multiplicities.

## [2.2.2]

### Fixed

- Import ABCs from `collections.abc` instead of `collections`. Fixes
  a `DeprecationWarning`.

## [2.2.1]

### Changed

- `rouver.test`: Use build-in `assert` statements instead of assertions
  from the `asserts` package.

## [2.2.0]

### Added

- Sub-routers now have access to WSGI environment variable
  called `rouver.original_path_info` that contains the original
  `PATH_INFO` value.

## [2.1.0]

### Added

- `rouver.args`: Add `"file-or-str"` argument value type.

### Changed

- `rouver.args`: Use `Literal`s for `ArgumentValueType`.

## [2.0.0]

### Added

- Add `TestRequest.add_file_argument()`.

### Changed

- Rework `TestRequest` argument handling.
  - Remove `TestRequest.prepare_for_arguments()`.
  - `TestRequest.content_type` will not be set when calling
    `add_argument()`.
- `ArgumentParser` and `parse_args()` will not raise a
  `BadRequest` if request has wrong content type. Instead,
  they will treat it as if no arguments were given.

### Removed

- Drop support for Python 3.5 and 3.6.

## [1.1.0]

### Added

- Add `absolute_url()` utility function.

### Changed

- URL constructing functions, such as `created_as_json()` now encode
  special characters in the path instead of throwing a `ValueError`.

## [1.0.0]

### Fixed

- `rouver.router`: Include extra headers from `HTTPException` sub-classes
  in responses.

## [0.99.2]

### Added

- `rouver.test`: Add pytest-friendly aliases:
  - `run_wsgi_test()` for `test_wsgi_app()`
  - `FakeRequest` for `TestRequest`
  - `FakeResponse` for `TestResponse`

## [0.99.1]

### Fixed

- `rouver.test`: Include `Content-Length` header when sending CGI
  arguments in request body (content type `application/x-www-form-urlencoded`).

## [0.99.0]

### Added

- `rouver.args`: Add `exhaustive` keyword-only argument to `parse_args()`,
  `ArgumentParser.parse_args()`, and `RouteHandlerBase.parse_args()`.

### Changed

- `parse_args()` is now implemented using werkzeug. While this does not
  change rouver's API, it may have incompatible side-effects or change the
  way CGI arguments are parsed slightly.
- Remove `CGIFileArgument`.

## [0.10.9]

### Fixed

- Import ABCs from `collections.abc` instead of `collections`. Fixes
  a `DeprecationWarning`.

## [0.10.8]

### Fixed

- Handle escaped URLs correctly.
- Path arguments are now decoded before being passed to the template handler.

## [0.10.7]

### Added

- `rouver.test`: Add `TestRequest.prepare_for_arguments()`.

## [0.10.6]

### Changed

- `rouver.test`: Include `CONTENT_LENGTH` in WSGI environment if body
  is set.

## [0.10.5]

### Added

- `rouver.test`: Add `TestRequest.body`.
- `rouver.test`: Add `TestRequest.set_json_body()`.

## [0.10.4]

### Added

- `rouver.test`: Add `TestResponse.parse_json_body()`.
- `rouver.test`: `TestResponse.assert_content_type()` now accepts a
  list of character sets.

## [0.10.3]

### Added

- `rouver.test`: Add `TestResponse.assert_set_cookie()`.

## [0.10.2]

### Fixed

- `rouver.test`: `assert_temporary_redirect()` et al. now work
  correctly with query strings and fragments.

## [0.10.1]

### Added

- `rouver.test`: Add `TestRequest.set_env_var()` and
  `TestRequest.set_header()`.
- `rouver.test`: Add `TestResponse.assert_header_not_set()`,
  `assert_content_type()`, `assert_see_other()`, and
  `assert_temporary_redirect()`.

## [0.10.0]

### Added

- `rouver.test`: New WSGI testing module.
- `rouver.response`: `created_at()`, `created_as_json()`,
  `temporary_redirect()`, and `see_also()` now take an optional
  `extra_headers` argument.

### Changed

- `rouver.types`: Replace `StartResponse`'s argument types with `...`
  `start_response()` takes either two or three arguments. This can not
  be modelled using type hints.

## [0.9.0]

### Added

- `rouver.response`: `created_at()`, `created_as_json()`,
  `temporary_redirect()`, and `see_other()` now support absolute URLs.

### Changed

- `rouver.response`: `created_at()`, `created_as_json()`,
  `temporary_redirect()`, and `see_other()` now treat URLs without a
  leading slash as relative to the request path.

### Fixed

- `rouver.html`: Replace `&mdash;` with `&#x2014;` for improved
  compatibility with XML parsers.

## [0.8.4]

### Added

- Add `py.typed` file to package `rouver` to enable type checking.

## [0.8.3]

### Added

- `rouver.handler`: Add `content_type` argument to
  `RouteHandlerBase.respond()`.

## [0.8.2]

### Added

- `rouver.response`: Add `content_type` argument to `respond()`.

### Fixed

- `rouver.args`: Raise `BadRequest` when a PATCH request has a wrong
  content type.

## [0.8.1]

### Fixed

- Fix sub-routers with non-ASCII paths.

## [0.8.0]

This release includes improvements against HTML injection attacks.

### Security

- `rouver.html`: `http_status_page()`: The `message` argument will now
  be HTML-escaped. Instead, an `html_message` argument was added.
  `content` was renamed to `html_content`.
- `rouver.html`: Harden all functions against malicious input.
- `rouver.router`: Correctly HTML-escape error messages.

## [0.7.0]

### Changed

- `rouver.response`: The following functions now only accept already
  URL-encoded partial URLs:
  - `created_at()`
  - `created_as_json()`
  - `temporary_redirect()`
  - `see_other()`
    Non-ASCII URLs with raise a `ValueError`.
- `rouver.handler`: See above.

## [0.6.1]

### Fixed

- `rouver.response`: Partial URLs in `temporary_redirect()` etc. were
  URL-encoded by accident.

## [0.6.0]

### Added

- `rouver.handler`: `RouteHandlerBase.respond`: Add `status` argument.

### Changed

- `rouver.handler`: `RouteHandlerBase.respond`: `extra_headers` is now a
  keyword-only argument.

## [0.5.5]

### Fixed

- `rouver.args`: `parse_args()` will now work for all methods, even if
  no arguments are supplied.

## [0.5.4]

### Fixed

- `rouver.handler`: `RouteHandlerBase.parse_args()` can now be called
  inside `prepare_response()`.

## [0.5.3]

### Added

- `rouver.args`: Add `ArgumentParser`.

### Changed

- `rouver.handler`: `RouteHandlerBase.parse_args()` can now be called
  multiple times.

## [0.5.2]

### Added

- `rouver.handler`: Add `RouteHandlerBase.parse_json_request()`.
- `rouver.handler`: Add `RouteHandlerBase.respond_with_content()`.
- `rouver.response`: Add `respond_with_content()`.

### Changed

- Include Content-Length header in JSON and HTML responses.

### Fixed

- Use first matching route handler, instead of crashing when multiple routes
  match.

## [0.5.1]

### Fixed

- `rouver.router`: Ignore trailing slashes.

## [0.5.0]

### Added

- `rouver.handler`: Add `RouterHandlerBase.wildcard_path`.
- `rouver.router`: Add a field `rouver.path_args` to the WSGI environment
  that contains the path arguments formerly passed to route handlers as the
  second argument. The wildcard path is not added to this field.
- `rouver.router`: Add a field `rouver.wildcard_path` to the WSGI
  environment that contains the wildcard path or the empty string.

### Changed

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

## [0.4.5]

### Added

- `rouver.router`: Support sub-routers.

## [0.4.4]

### Added

- `rouver.router`: Support wildcard paths.

## [0.4.3]

### Fixed

- `rouver.response`: Quote non-UTF-8 URLs correctly in Location headers.

## [0.4.2]

### Added

- `rouver.handler`: Add `RouteHandlerBase.temporary_redirect()` and
  `created_as_json()`.
- `rouver.html`: Add `temporary_redirect_page()`.
- `rouver.response`: Add `temporary_redirect` and `created_as_json()`.

### Fixed

- `rouver.router`: Fix nested <p> element in error pages.

## [0.4.1]

### Fixed

- `rouvers.args`: `parse_args()` will now throw a `BadRequest` if
  the Content-Type is incorrect for POST and PUT requests.

## [0.4.0]

### Added

- `rouver.types`: Add `WSGIApplication` and `WSGIResponse`.

### Changed

- `rouver.types`: Rename `HeaderType` to `Header`.
- `rouver.types`: Rename `EnvironmentType` to `WSGIEnvironment`.
- `rouver.types`: Rename `StartResponseType` to `StartResponse`.
- `rouver.types`: Rename `RouteType` to `RouteDescription`.

## [0.3.1]

### Changed

- Type hinting: Use `Sequence` over `List` and `Mapping` over `Dict` in
  function/method arguments.

### Fixed

- `rouver.html`: Fix argument types of `bad_arguments_page()` and
  `bad_arguments_list()`.

## [0.3.0]

### Added

- `rouver.html`: `http_status_page()`: Add new optional argument
  `content`.
- `rouver.html`: Add `bad_arguments_list()`.
- `rouver.types`: Add `BadArgumentsDict`.

### Changed

- `rouver.html`: `http_status_page()`: `message` argument is now an
  optional, keyword-only argument.
- `rouver.router`: Template handlers must now be installed before calling
  `add_routes()`.
- `rouver.router`: Router now returns a custom error page when
  `ArgumentsError` is raised.

## [0.2.1]

### Fixed

- `rouver.handler`: Derive `RouteHandlerBase` from `Iterable`.
- `rouver.response`/`rouver.handler`: Fix return types of response methods.

## [0.2.0]

### Added

- `rouver.handler`: Add `RouteHandlerBase`.
- `rouver.html`: Add `created_at_page()`.
- `rouver.response`: Add `respond_ok()`, `respond_with_json()`, and
  `created_at()`.

## [0.1.1]

### Changed

- `rouver.response`: Responses now return an iterator so they can be used as
  return values from `__iter__()` methods.

## [0.1.0]

### Added

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
