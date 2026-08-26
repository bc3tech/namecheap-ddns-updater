---
title: "feat: Add Namecheap Dynamic DNS proxy"
type: feat
status: completed
date: 2026-08-26
---

# feat: Add Namecheap Dynamic DNS proxy

## Overview

Create a small Flask application that accepts `hostname`, `ipAddress`, and `key`
as query parameters and forwards them to Namecheap's Dynamic DNS update endpoint.
Package the application for Python 3.14 in a minimal Docker image.

## Problem Frame

The application provides a thin HTTP proxy so a caller can use one local endpoint
instead of constructing the Namecheap Dynamic DNS request directly.

## Requirements Trace

- R1. Accept `hostname`, `ipAddress`, and `key` query parameters.
- R2. Derive the Namecheap `host` and `domain` values from `hostname`, preserving
  wildcard (`*`) and apex (`@`) host values.
- R3. Make a GET request to the Namecheap update endpoint with the derived values.
- R4. Return the upstream result without adding unrelated behavior.
- R5. Run in a Python 3.14 Docker container.

## Scope Boundaries

- No database, authentication layer, background jobs, configuration UI, or
  persistent state.
- No DNS validation or public-suffix database; hostname parsing uses the final
  two labels as the domain and the preceding labels as the subdomain.
- No retries or response transformation beyond proxying the upstream status and
  body.

## Context & Research

### Relevant Code and Patterns

- The repository is empty aside from Git metadata; this is a greenfield layout.
- Use a small application module, a pytest test module, dependency metadata, and
  a Dockerfile.

### Institutional Learnings

- No `docs/solutions/` or existing project conventions are present.

### External References

- Namecheap Dynamic DNS update endpoint:
  `https://dynamicdns.park-your-domain.com/update`

## Key Technical Decisions

- **Use Flask with a synchronous HTTP client:** the proxy has one upstream call
  per request, so asynchronous infrastructure would add complexity without value.
- **Use an explicit upstream timeout:** the proxy must not hold worker capacity
  indefinitely when Namecheap is unavailable.
- **Forward upstream status and response body:** this preserves the simple proxy
  contract and avoids inventing an interpretation of Namecheap's response.
- **Use a production WSGI server in Docker:** the development server is not an
  appropriate container entrypoint.

## Open Questions

### Resolved During Planning

- The endpoint path is `/update`.
- Missing required parameters are client errors.
- A hostname's final two labels form `domain`; all preceding labels form `host`.
  A hostname containing only the domain maps to host `@`.

### Deferred to Implementation

- Exact module and function names can follow the implementation's minimal layout.
- Exact upstream timeout can be selected as a small bounded value suitable for a
  lightweight proxy.

## High-Level Technical Design

> This illustrates the intended approach and is directional guidance for review,
> not implementation specification. The implementing agent should treat it as
> context, not code to reproduce.

```text
HTTP GET /update
  -> validate hostname, ipAddress, key
  -> split hostname into host + domain
  -> construct Namecheap query parameters
  -> GET Namecheap endpoint with timeout
  -> return upstream body and status
```

## Implementation Units

- [x] **Unit 1: Create the Flask proxy endpoint**

**Goal:** Implement the single endpoint and hostname-to-Namecheap parameter
mapping.

**Requirements:** R1, R2, R3, R4

**Dependencies:** None

**Files:**
- Create: `app.py`
- Test: `tests/test_app.py`

**Approach:**
- Require all three query parameters and return a client error when any is
  missing or blank.
- Parse the final two hostname labels as `domain`; preserve all earlier labels
  as the full `host`, including `*` and `@`.
- Use a bounded timeout for the upstream GET.
- Return upstream response text and status code directly; surface upstream
  request failures as a server-side error.

**Patterns to follow:**
- Keep the application as a single small Flask module because the repository has
  no existing architecture to preserve.

**Test scenarios:**
- Happy path — `hostname=www.example.com`, `ipAddress=192.0.2.10`, and
  `key=secret` produce `host=www`, `domain=example.com`, and the expected
  upstream request.
- Happy path — `hostname=foo.bar.example.com` preserves `host=foo.bar`.
- Edge case — `hostname=*.example.com` produces `host=*`.
- Edge case — `hostname=@.example.com` produces `host=@`.
- Edge case — `hostname=example.com` maps to `host=@`.
- Error path — each missing or blank required parameter returns a client error
  without calling Namecheap.
- Error path — an invalid hostname without a domain portion returns a client
  error without calling Namecheap.
- Error path — an upstream timeout or connection failure returns a server error.
- Integration — the route returns the upstream body and status code received
  from a mocked Namecheap response.

**Verification:**

- The endpoint makes exactly one correctly parameterized GET request for valid
  input and returns the upstream response.

- [x] **Unit 2: Add runtime dependencies and container packaging**

**Goal:** Make the proxy runnable with Python 3.14 and Docker.

**Requirements:** R5

**Dependencies:** Unit 1

**Files:**
- Create: `requirements.txt`
- Create: `Dockerfile`
- Create: `.dockerignore`

**Approach:**
- Base the image on the Python 3.14 slim image.
- Install only Flask, the synchronous HTTP client, and the production WSGI
  server needed by the application.
- Run the WSGI server bound to all container interfaces on the standard
  application port.
- Exclude local caches, virtual environments, Git metadata, and test artifacts
  from the build context.

**Patterns to follow:**
- No repository packaging conventions exist; use conventional minimal Docker
  packaging for a single-service Flask application.

**Test scenarios:**
- Test expectation: none -- this unit is runtime packaging; its behavior is
  verified by starting the image and reaching the Flask endpoint.

**Verification:**

- The image builds from the repository root and starts the proxy with Python 3.14
  without requiring files outside the build context.

## System-Wide Impact

- **Interaction graph:** A caller reaches the Flask route, which makes one
  outbound request to Namecheap and returns the result.
- **Error propagation:** Input errors remain client errors; upstream transport
  failures become server errors; upstream HTTP status and body are preserved.
- **State lifecycle risks:** No application state or persistence is introduced.
- **API surface parity:** Only the new Flask route is exposed.
- **Integration coverage:** Route tests must verify the exact outbound query
  parameters and returned upstream response.
- **Unchanged invariants:** The proxy does not alter Namecheap's response format
  or provide a second DNS update mechanism.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| The upstream request can hang | Apply a bounded HTTP timeout. |
| The DNS key appears in the outbound URL and may be logged | Do not log query parameters or full upstream URLs. |
| Hostname parsing can be ambiguous for multi-label public suffixes | Keep the documented final-two-label rule and avoid pretending to support a public-suffix database. |
| The upstream service can return errors or malformed content | Preserve its status/body and surface transport failures explicitly. |

## Documentation / Operational Notes

- Add a concise `README.md` documenting the route, query parameters, hostname
  parsing rule, and Docker run usage.
- Keep the container port and upstream endpoint discoverable in the README.

## Sources & References

- Related code: none; repository is greenfield.
- External endpoint: https://dynamicdns.park-your-domain.com/update
