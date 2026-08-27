# Namecheap Dynamic DNS Proxy

This small Flask service forwards DNS update requests to Namecheap.

## Deploy to Azure

The project is configured for Azure Container Apps through the Azure Developer
CLI (`azd`). The container is built for `linux/amd64` and listens on port 80.

Install the [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd),
authenticate, and run the deployment from the repository root:

```text
azd auth login
azd up
```

`azd up` provisions the Azure Container Registry, Application Insights,
Container Apps environment, and Container App. It builds this project into a
container image, pushes the image to the registry, and deploys it to the
Container App. After it completes, retrieve the public Container Apps URL with:

```text
azd show
```

Copy the HTTPS URL shown under **Services**. Use that URL when configuring the
NAS below.

For later application or Dockerfile changes, run `azd deploy` again.
The Container App scales to zero when idle and never uses more than one
replica; azd reapplies these bounds after provisioning and deployment.

### Enable Application Insights

The app uses the Azure Monitor OpenTelemetry distro. The azd Container Apps
resource automatically provisions a workspace-based Application Insights
resource and configures the Container App's
`APPLICATIONINSIGHTS_CONNECTION_STRING` environment variable with its
connection string. Keep the connection string out of source control.

With the setting present, the app automatically reports Flask requests,
outbound Namecheap requests, application logs, metrics, and exceptions to
Application Insights. Without it, the app continues to run locally with
console logging only.

## Run with Docker

```text
docker build -t namecheap-ddns-proxy .
docker run --rm -p 7780:80 namecheap-ddns-proxy
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

After deploying to Azure, open **Control Panel > External Access > DDNS** in
DSM and create a **Customized DDNS Provider**. Replace
`<container-app-hostname>` with the hostname from the HTTPS URL returned by
`azd show` (do not include `https://` or a port):

```text
https://<container-app-hostname>/update?host=__USERNAME__&domain=__HOSTNAME__&******
```

Add a DDNS entry using that customized provider and configure:

- **Hostname:** the Namecheap domain, such as `example.com`
- **Username/Email:** the Namecheap host, such as `home` or `@`
- **Password/Key:** the Namecheap Dynamic DNS password
- **External Address (IPv4):** `Auto`

DSM will call the Azure endpoint over HTTPS, so the NAS does not need a
port-forwarding rule or a local address for this proxy. Use the Azure hostname,
not `localhost` or the NAS LAN address.

For example, if the Namecheap record is `home.example.com`, use:

- **Hostname:** `example.com`
- **Username/Email:** `home`

For the apex record `example.com`, use `@` as the username/host. Test or save
the DDNS entry in DSM; a successful update returns `good`.

The proxy also accepts the original `hostname`, `ipAddress`, and `key`
parameters at `/update`. For Synology, the documented route and parameter names
above are recommended. It returns the standard DDNS responses `good`, `nohost`,
`badauth`, or `911` with HTTP 200 so DSM can interpret the result.
