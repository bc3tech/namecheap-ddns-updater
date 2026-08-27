# Namecheap Dynamic DNS Proxy

This Flask service accepts Dynamic DNS update requests and forwards them to
Namecheap. It is designed for Synology DSM, but it also supports Namecheap's
legacy parameter names.

The only application route is `GET /update`. Responses use the standard DDNS
values `good`, `nohost`, `badauth`, and `911`, all with HTTP 200 so DSM can
interpret them.

## Deploy to Azure

### Prerequisites

Install and authenticate the following tools:

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- [Docker](https://docs.docker.com/get-docker/)

You also need a Namecheap domain with Dynamic DNS enabled and its Dynamic DNS
password. See [Namecheap's Dynamic DNS
instructions](https://www.namecheap.com/support/knowledgebase/article.aspx/595/11/how-do-i-enable-dynamic-dns-for-a-domain/).

From the repository root, sign in:

```powershell
az login
azd auth login
```

### Provision and deploy

Run:

```powershell
azd up
```

On the first run, azd asks for the Azure subscription and location. To set
them without prompts for a new named azd environment:

```powershell
azd up --environment namecheap-ddns --subscription <subscription-id> --location westus3
```

Alternatively, select an existing environment and set its values before
running `azd up`:

```powershell
azd env select namecheap-ddns
azd env set AZURE_SUBSCRIPTION_ID <subscription-id>
azd env set AZURE_LOCATION westus3
azd up
```

`azd up` builds this project into a `linux/amd64` container image, pushes it
to the Azure Container Registry, and deploys it to Azure Container Apps. The
project intentionally defines `project: .` rather than a pre-built `image:`,
so azd owns the build and publish workflow.

The azd-managed resources include:

- Azure Container Registry
- Workspace-based Application Insights
- Log Analytics
- Container Apps environment
- The Dynamic DNS proxy Container App

The Container App scales to zero when idle and is limited to one replica.
azd reapplies these limits after provisioning and deployment. Scale-to-zero
can cause a cold-start delay on the first request, and the supporting Azure
resources can still incur charges. To remove the deployment and its ongoing
resource charges:

```powershell
azd down
```

Retrieve the deployed HTTPS endpoint with:

```powershell
azd show
```

Copy the URL shown under **Services**. Use the hostname from that URL when
configuring DSM.

For later application or Dockerfile changes, run:

```powershell
azd deploy
```

### Application Insights

The application uses the Azure Monitor OpenTelemetry distro. The azd-managed
Container App receives `APPLICATIONINSIGHTS_CONNECTION_STRING` from the
workspace-based Application Insights resource. No manual environment-variable
configuration is required.

When the connection string is present, the application reports Flask
requests, outbound Namecheap requests, application logs, metrics, and
exceptions to Application Insights. Without it, local execution uses console
logging only.

## Run locally

### Python

Requires Python 3.14.

Create a virtual environment and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Start the development server:

```powershell
python app.py
```

The server listens on `http://localhost:7780` by default. To use another
port:

```powershell
$env:PORT = "8000"
python app.py
```

### Docker

Build and run the production container:

```powershell
docker build -t namecheap-ddns-proxy .
docker run --rm -p 7780:80 namecheap-ddns-proxy
```

The container listens on port `80`; the example maps it to port `7780` on the
local machine. View container logs with:

```powershell
docker ps
docker logs -f <container-id>
```

## Send an update

Keep the Namecheap Dynamic DNS key in a local variable rather than placing it
in source code or a documented URL. This example uses the legacy parameter
names:

```powershell
$namecheapKey = Read-Host "Namecheap Dynamic DNS key"
curl.exe --get "http://localhost:7780/update" `
    --data-urlencode "hostname=home.example.com" `
    --data-urlencode "ipAddress=192.0.2.10" `
    --data-urlencode "key=$namecheapKey"
```

`192.0.2.10` is documentation-only; replace it with the address that should
be written to Namecheap.

The supported parameter forms are:

| Use | Parameters |
| --- | --- |
| Legacy | `hostname`, `ipAddress`, `key` |
| Synology split | `host`, `domain`, `password`, and `ip` or `myip` |
| Synology username | `username`, `hostname`, `password`, and `ip` or `myip` |

For legacy `hostname` requests, the final two labels become the domain and
all preceding labels become the host. A hostname with no subdomain uses `@`.
Wildcard and apex values such as `*.example.com` and `@.example.com` are
preserved.

Responses have these meanings:

| Response | Meaning |
| --- | --- |
| `good` | Namecheap accepted the update |
| `nohost` | The domain or DNS host was not found |
| `badauth` | A required parameter is missing or the key is invalid |
| `911` | The upstream request failed or returned an invalid response |

## Configure Synology DSM

After deploying to Azure, open **Control Panel > External Access > DDNS** in
DSM and create a **Customized DDNS Provider**.

Replace `<container-app-hostname>` with the hostname from `azd show`. Do not
include `https://` or a port. Keep DSM's `******` password placeholder in the
URL:

```text
https://<container-app-hostname>/update?host=__USERNAME__&domain=__HOSTNAME__&******
```

Add a DDNS entry using that provider:

| DSM field | Value |
| --- | --- |
| Hostname | The Namecheap domain, such as `example.com` |
| Username/Email | The Namecheap host, such as `home` or `@` |
| Password/Key | The Namecheap Dynamic DNS password |
| External Address (IPv4) | `Auto` |

For the record `home.example.com`, use `example.com` as the hostname and
`home` as the username. For the apex record `example.com`, use `@` as the
username/host.

DSM calls the Azure endpoint over HTTPS, so the NAS does not need a
port-forwarding rule or a local address for this proxy. Use the Azure
hostname, not `localhost` or the NAS LAN address.

## Test and troubleshoot

Run the test suite:

```powershell
python -m unittest discover -s tests -v
```

Check Python syntax:

```powershell
python -m py_compile app.py tests\test_app.py
```

If a request returns `badauth`, check the parameter names and confirm that the
Namecheap key is the Dynamic DNS password. If it returns `nohost`, check the
domain and host values. If it returns `911`, inspect the application logs for
timeout, connection, HTTP status, or XML parsing errors without exposing the
Namecheap key.

Never commit or log the Namecheap key. Prefer HTTPS whenever the proxy is
deployed outside local development.
