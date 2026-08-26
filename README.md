# Namecheap Dynamic DNS Proxy

This small Flask service forwards DNS update requests to Namecheap.

## Run with Docker

```text
docker build --build-arg PORT=7780 -t namecheap-ddns-proxy .
docker run --rm -p 7780:7780 namecheap-ddns-proxy
```

Successful upstream responses are logged with the hostname, derived host and
domain, IP address, and status code. Request validation, upstream requests,
response parsing, response mapping, and failures are also logged. The Namecheap
key is never logged. When running the container, view these messages with
`docker logs -f <container-id>`.

If your environment uses an internal Python package mirror, pass it during the
build with `--build-arg PIP_INDEX_URL=<mirror-url>`.

Call the proxy with `hostname`, `ipAddress`, and `key` query parameters:

```text
http://localhost:7780/update?hostname=home.example.com&ipAddress=192.0.2.10&key=your-key
```

The final two hostname labels become `domain`, and preceding labels become
`host`. A hostname with no subdomain uses `@`; wildcard and apex values such as
`*.example.com` and `@.example.com` are preserved.

## Configure Synology DSM

Create a **Customized DDNS Provider** with this query URL:

```text
http://<nas-address>:7780/update?host=__USERNAME__&domain=__HOSTNAME__&password=__PASSWORD__&ip=__MYIP__
```

Use the NAS LAN address or a hostname resolvable by DSM rather than
`localhost`. Configure the DDNS entry with:

- **Hostname:** the Namecheap domain, such as `example.com`
- **Username/Email:** the Namecheap host, such as `home` or `@`
- **Password/Key:** the Namecheap Dynamic DNS password
- **External Address (IPv4):** `Auto`

The proxy also accepts the original `hostname`, `ipAddress`, and `key`
parameters at `/update`. For Synology, the documented route and parameter names
above are recommended. It returns the standard DDNS responses `good`, `nohost`,
`badauth`, or `911` with HTTP 200 so DSM can interpret the result.
