# Namecheap Dynamic DNS Proxy

This small Flask service forwards DNS update requests to Namecheap.

## Run with Docker

```text
docker build -t namecheap-ddns-proxy .
docker run --rm -p 8080:8080 namecheap-ddns-proxy
```

If your environment uses an internal Python package mirror, pass it during the
build with `--build-arg PIP_INDEX_URL=<mirror-url>`.

Call the proxy with `hostname`, `ipAddress`, and `key` query parameters:

```text
http://localhost:8080/update?hostname=home.example.com&ipAddress=192.0.2.10&key=your-key
```

The final two hostname labels become `domain`, and preceding labels become
`host`. A hostname with no subdomain uses `@`; wildcard and apex values such as
`*.example.com` and `@.example.com` are preserved.
