# Running Tests

## Excluding E2E Tests

E2E tests require a running server and are marked with `@pytest.mark.integration` and `@pytest.mark.slow`.

### Option 1: Exclude by directory
```bash
pytest tests/ --ignore=tests/e2e
```

### Option 2: Exclude by marker
```bash
pytest tests/ -m "not integration"
```

### Option 3: Exclude both slow and integration tests
```bash
pytest tests/ -m "not slow and not integration"
```

### Option 4: Run only unit tests (exclude e2e directory and integration markers)
```bash
pytest tests/ --ignore=tests/e2e -m "not integration"
```

### Option 5: Quick command to skip e2e tests (recommended)
```bash
pytest tests/ --ignore=tests/e2e -m "not integration and not slow"
```

## Running Specific Test Files

```bash
# Run only router tests
pytest tests/test_hybrid_routes.py

# Run only app tests
pytest tests/test_app.py

# Run only server tests
pytest tests/test_server.py
```

## Debugging 422 Errors

If you see 422 (Unprocessable Entity) errors, check the response body for validation details:

```python
response = await client.post("/endpoint", json={...})
if response.status_code == 422:
    print(response.json())  # Shows validation errors
```

## Common Issues

1. **422 Validation Errors**: Usually means the request body doesn't match the expected schema
2. **Dependency Override Issues**: Make sure dependency overrides are set BEFORE including routers
3. **E2E Tests Failing**: These require a running server on the configured port

