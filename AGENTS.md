# AGENTS.md

## Project Overview

Namecheap Dynamic DNS Proxy is a small Flask service that accepts Dynamic DNS
update requests and forwards them to Namecheap's update endpoint.

- Application: `app.py`
- Tests: `tests\test_app.py`
- Runtime: Python 3.14
- Container: Docker with Gunicorn
- Azure deployment: Azure Developer CLI (`azd`) to Azure Container Apps
- Persistence: none; there is no database or background worker

The only application route is `GET /update`. It accepts the legacy
`hostname`, `ipAddress`, and `key` parameters, plus the Synology-compatible
`host`, `domain`, `password`, and IP parameter aliases. Responses are plain
text and use the DDNS protocol values `good`, `nohost`, `badauth`, or `911`,
all with HTTP 200 so Synology DSM can interpret them.

## Setup Commands

Create and activate a local virtual environment in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The runtime dependencies are Flask, Requests, and Gunicorn. There is no
`pyproject.toml`, package-lock file, or separate build system.

## Development Workflow

Run the Flask development server from the repository root:

```powershell
python app.py
```

The server listens on `0.0.0.0` and defaults to port `7780`. Set the `PORT`
environment variable to use another port:

```powershell
$env:PORT = "8000"
python app.py
```

Example request:

```text
http://localhost:7780/update?hostname=home.example.com&ipAddress=192.0.2.10&key=your-key
```

For `hostname` requests, the final two labels become `domain` and all
preceding labels become `host`. A hostname containing only the domain maps to
the apex host `@`; wildcard and apex values such as `*.example.com` and
`@.example.com` are preserved.

## Testing Instructions

Run the complete test suite:

```powershell
python -m unittest discover -s tests -v
```

Run a specific test:

```powershell
python -m unittest tests.test_app.UpdateDnsTests.test_supports_legacy_parameter_names -v
```

Check Python syntax and compilation:

```powershell
python -m py_compile app.py tests\test_app.py
```

Tests use the standard-library `unittest` framework and Flask's test client.
Requests to Namecheap are mocked, so the test suite does not require network
access. Add or update tests in `tests\test_app.py` when changing request
parsing, validation, upstream error handling, or response mapping.

No repository linter or formatter is configured. Do not introduce a new
toolchain for routine changes; preserve the existing Python formatting and
typing style.

## Code Style

- Use four spaces for indentation and keep imports grouped as in `app.py`.
- Prefer clear type annotations for helper function inputs and return values.
- Keep the service small and synchronous; avoid adding abstractions,
  persistence, retries, or background jobs without a concrete requirement.
- Use the existing Flask route and helper functions for request parsing and
  response handling.
- Preserve the bounded Namecheap request timeout.
- Keep logs structured with parameter values that are safe to emit.
- Never log the Namecheap key or include it in diagnostic messages.

## Build and Deployment

Build and run the production container from the repository root:

```powershell
docker build -t namecheap-ddns-proxy .
docker run --rm -p 7780:80 namecheap-ddns-proxy
```

The Docker image uses `python:3.14-slim`, installs `requirements.txt`, and
starts Gunicorn on `0.0.0.0:${PORT}`. The default container port is `80`.

The Azure deployment is defined by `azure.yaml` and targets Azure Container
Apps using the `linux/amd64` Docker platform:

```powershell
azd auth login
azd up
azd show
azd deploy
```

Use `azd up` for initial provisioning and deployment, `azd show` to retrieve
the deployed service URL, and `azd deploy` for later application or Dockerfile
changes. The `.azure` directory contains local Azure Developer CLI state and
must not be committed.

## Security Considerations

- Treat the Namecheap Dynamic DNS key as a secret. Do not commit it, print it,
  or add it to logs, test fixtures intended for production, or URLs in
  documentation.
- Use HTTPS and restrict access to the deployed proxy where possible because
  the request carries the Dynamic DNS credential.
- Do not log complete incoming query strings or outbound URLs containing
  credentials.
- Keep `.venv`, Python caches, test artifacts, and `.azure` state out of
  commits.
- Preserve explicit upstream timeouts and return `911` for transport failures
  or malformed upstream responses.

## Pull Request Guidelines

Keep changes focused on the proxy, its tests, or its documented deployment
workflow. Before submitting a change, run the unittest suite and Python
compilation check above, and update `README.md` when the public request,
container, or deployment workflow changes. No repository-specific pull
request title or commit-message format is documented.

## Troubleshooting

- If the local server uses the wrong port, check the `PORT` environment
  variable; the local default is `7780`, while the container default is `80`.
- If a valid-looking hostname is rejected, verify the documented final-two-label
  parsing rule and the required query parameter names.
- If a request returns `911`, inspect the application logs for timeout,
  connection, HTTP status, or XML parsing failures without exposing the key.
