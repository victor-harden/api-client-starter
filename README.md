# api-client-starter

A dependency-free HTTP client skeleton you can adapt to any JSON API: timeouts,
bounded retries with exponential backoff, typed errors, JSON helpers and an auth
token read from the environment.

## Features

- `ApiClient` with `base_url`, default headers, timeout and retry policy.
- Retries on connection errors and 5xx/429 responses, never on 4xx.
- `get_json` / `post_json` helpers that raise clear errors on bad responses.
- Token from `API_TOKEN` environment variable, never hardcoded.
- Tests run against a local HTTP server and simulate failures.

## Installation

```bash
git clone https://github.com/victor-harden/api-client-starter.git
cd api-client-starter
```

## Usage

```python
from api_client import ApiClient

client = ApiClient("https://httpbin.org", retries=2, timeout=5)
print(client.get_json("/get"))
```

```bash
API_TOKEN=secret python3 -c "from api_client import ApiClient; print(ApiClient('https://example.com').token is not None)"
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## License

MIT — see [LICENSE](LICENSE).
