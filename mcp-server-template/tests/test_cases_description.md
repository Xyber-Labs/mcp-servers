Unit tests:

1) All routers are unit-tested against the real FastAPI routes and schemas.

Happy path:
- Each endpoint is called with a declared payload (as in the OpenAPI/Swagger schema).
- For discrete parameters (literals, booleans) we cover each allowed option; for example:
  - `/hybrid/current` is exercised with `units=None`, `"metric"`, and `"imperial"`.
    - Implemented by: `tests/test_hybrid_routes.py::test_get_current_weather_returns_serialised_weather` (parametrised over `units`).
  - MCP tools are covered both as hybrid (REST + MCP) and MCP-only flows.
    - Implemented by:
      - `tests/test_mcp_routes.py::test_get_weather_analysis_returns_text`
      - `tests/test_mcp_routes.py::test_geolocate_city_returns_coordinates`
- For continuous parameters (floats/ints), we pick representative values from different ranges; for example:
  - `/hybrid/forecast` uses `days=3` in the happy path.
    - Implemented by: `tests/test_hybrid_routes.py::test_get_weather_forecast_returns_forecast_payload`.

Additionally, the basic API routers are covered:
- `/api/health` returns 200 with service metadata.
  - Implemented by: `tests/test_api_routes.py::test_health_endpoint_returns_ok`.
- `/api/admin/logs` returns 200 with a list of logs in the unit/in-process context (no x402).
  - Implemented by: `tests/test_api_routes.py::test_admin_logs_returns_log_entries`.

Edge Cases:
- When `ge`/`le` validation is present:
  - If `ge > 0`, we include tests for -1, 0, 1.
  - If `le < 100`, we include tests for 99, 100, 101.
- In this service, `/hybrid/forecast` enforces `days` via `Query(ge=1, le=14)`:
  - We test values just outside the range (`days=0` and `15`) and assert FastAPI returns `422`.
    - Implemented by: `tests/test_hybrid_routes.py::test_get_weather_forecast_days_out_of_range_returns_422` (parametrised over `days`).
Bad Path:

Malformed input:
- Empty body or missing required fields.
- Payloads not in accordance with the schema.
- Out-of-range values for parameters with `ge`/`le`.

For example:
- `/hybrid/current` has a test that sends an empty JSON body and asserts a `422` validation error from FastAPI.
  - Implemented by: `tests/test_hybrid_routes.py::test_get_current_weather_empty_body_returns_422`.
- `/hybrid/forecast` has tests that send out-of-range `days` values and expects `422`.
  - Implemented by: `tests/test_hybrid_routes.py::test_get_weather_forecast_days_out_of_range_returns_422`.

2) x402 wrapper unit test:

The x402 wrapper is treated as a first-class public surface:
- It is mounted on a tiny FastAPI app in `tests/middlewares/test_x402_wrapper.py`.
- Pricing is injected via `PaymentOption` fixtures.
- `get_x402_settings` and `FacilitatorClient` are monkey-patched to deterministic stubs so that verification and settlement do not touch external systems.

Happy path:
- free to use endpoints pass easily
- paid endpoints return 402 response
- if request contains VALID x402 payments - verification with faciliatotor is hapenning
	- very important! 

In practice:
- Free endpoints bypass the middleware and are covered by router tests.
- Paid endpoints:
  - Return 402 with a valid `x402PaymentRequiredResponse` when the `X-PAYMENT` header is missing or invalid.
  - Accept a valid `X-PAYMENT` header generated using the same logic as `x402HttpxClient`:
    - We first call the endpoint to get the 402 body and its `accepts` list.
    - We construct a real payment header from those requirements.
    - On the second call the middleware verifies the payment via the stub facilitator, allows the request to pass, and attaches an `X-PAYMENT-RESPONSE` header when settlement succeeds.

Bad path:
- what if x - payment header contains no matching information?
Bad-path coverage includes:
- Sending syntactically valid but semantically mismatched payment headers (e.g. wrong network or asset), which results in a `402` response with the error `"No matching payment requirements found"`.

Implemented by:
- `tests/middlewares/test_x402_wrapper.py::test_missing_payment_header_returns_402`
  - No `X-PAYMENT` header → 402 with valid x402 body (`accepts` list, `error` message).
- `tests/middlewares/test_x402_wrapper.py::test_invalid_payment_header_returns_402`
  - Malformed (non-JSON) `X-PAYMENT` header → 402 with `"Invalid payment header format"`.
- `tests/middlewares/test_x402_wrapper.py::test_valid_payment_header_allows_request_and_sets_response_header`
  - Real header created via `x402Client` → 200 response, `X-PAYMENT-RESPONSE` header set, facilitator stub `verify`/`settle` called.
- `tests/middlewares/test_x402_wrapper.py::test_payment_header_with_wrong_network_returns_no_matching`
  - Tampered `network` field → 402 with `"No matching payment requirements found"`.

3) weather client test:

public methods: 
get_weather()
Happy path:
- input are latitude and longitude as str, units as literal
Should return WeatherData

The client’s happy path is backed by unit tests that:
- Inject a realistic OpenWeatherMap-like JSON payload.
- Assert that `get_weather` returns a `WeatherData` instance.
- Confirm that the result is stored in an internal cache for subsequent calls.

Implemented by:
- `tests/weather/test_client.py::test_get_weather_success`
  - Happy-path HTTP 200 with realistic payload → `WeatherData` instance with expected fields.
- `tests/weather/test_client.py::test_get_weather_uses_cache`
  - Two calls with same coordinates → only one underlying HTTP call due to caching.

Edge cases include:
- Cache behaviour: miss, hit, and expiry after TTL.
- HTTP failures:
  - 5xx responses from the upstream API are converted into `WeatherApiError` via `HTTPStatusError` handling.
  - Connection-level issues raise `WeatherApiError` via `RequestError` handling.
- Parsing failures:
  - Missing fields in the JSON payload result in `WeatherClientError` (e.g. `KeyError` from the model factory).
- Unexpected exceptions are wrapped as `WeatherClientError` while preserving the original cause.

Implemented by:
- `tests/weather/test_client.py::test_cache_expires`
  - Short cache TTL + time travel → second call after expiry triggers a new HTTP request and returns updated data.
- `tests/weather/test_client.py::test_http_error_translates_to_weather_api_error`
  - Mocked 500 `HTTPStatusError` from `httpx` → `WeatherApiError` raised by `get_weather`.
- `tests/weather/test_client.py::test_parsing_error_translates_to_weather_client_error`
  - Payload missing required fields → `WeatherClientError` raised during parsing.
- `tests/weather/test_client.py::test_close_closes_underlying_http_client`
  - `WeatherClient.close()` calls `aclose()` on the underlying HTTP client.
- (To be added) explicit coverage for "unexpected generic exceptions wrapped as `WeatherClientError` with preserved `__cause__`."

Bad path:
wrong latitude/longitude
wrong units

For now the client forwards whatever strings it receives to OpenWeatherMap. If we later introduce local validation (regex/range) for coordinates or units, we will:
- Add unit tests that pass clearly invalid coordinates or unsupported units.
- Assert that `WeatherClientError` is raised without attempting an upstream call.

with mypy(and configuration tests), so explicit unit tests are not required
No more public methods!

=================================
Test-cases for end-to-end final test

MCP server weather:

Happy Path:
- All 6 endpoints work if we follow the schema.
- If an endpoint has multiple payment options - we can follow any of them, all work.
- If an endpoint is hybrid - it works both with REST and MCP.

This is enforced by the pytest-based E2E suite under `tests/e2e`:

- **REST-only:**
  - `/api/health`:
    - Implemented by: `tests/e2e/test_rest_only.py::test_health_endpoint_available`
  - `/api/admin/logs`:
    - 402 without payment:
      - Implemented by: `tests/e2e/test_rest_only.py::test_admin_logs_requires_payment`
    - 200 with x402 payment:
      - Implemented by: `tests/e2e/test_rest_only.py::test_admin_logs_succeeds_with_x402`

- **Hybrid (REST + MCP context):**
  - `/hybrid/current` via REST:
    - Implemented by: `tests/e2e/test_hybrid.py::test_hybrid_current_via_rest`
  - `/hybrid/forecast`:
    - 402 without payment:
      - Implemented by: `tests/e2e/test_hybrid.py::test_hybrid_forecast_requires_payment`
    - Successful paid call (when environment is fully wired):
      - Implemented by: `tests/e2e/test_hybrid.py::test_hybrid_forecast_succeeds_with_x402`

- **MCP-only tools:**
  - `geolocate_city`:
    - Implemented by: `tests/e2e/test_mcp_only.py::test_mcp_geolocate_city_tool`
  - `get_weather_analysis` (priced MCP tool):
    - currently expected to return 402 without payment:
      - Implemented by: `tests/e2e/test_mcp_only.py::test_mcp_weather_analysis_tool_requires_payment`

Edge cases for end-to-end tests include:
- Multiple priced options for the same `operation_id`, ensuring the client can successfully pay with any configured asset/network.
- Malformed or missing fields in live requests (wrong parameter names, bad JSON) returning structured error messages from FastAPI or MCP.

Bad-path behaviour includes:
- 402 responses with clear `error` messages for missing or invalid `X-PAYMENT` headers.
- 402 responses with `"No matching payment requirements found"` when the payment header network/asset does not align with the configured pricing.
- 4xx responses from FastAPI for invalid request bodies or query parameters, with helpful `detail` fields describing the validation failure.
