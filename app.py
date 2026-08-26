from flask import Flask, make_response, request
import requests


NAMECHEAP_UPDATE_URL = "https://dynamicdns.park-your-domain.com/update"
UPSTREAM_TIMEOUT_SECONDS = 10

app = Flask(__name__)


def parse_hostname(hostname: str) -> tuple[str, str]:
    labels = hostname.strip().rstrip(".").split(".")
    if len(labels) < 2 or any(not label for label in labels):
        raise ValueError("hostname must include a domain and suffix")

    domain = ".".join(labels[-2:])
    host = ".".join(labels[:-2]) or "@"
    return host, domain


@app.get("/update")
def update_dns():
    hostname = request.args.get("hostname")
    ip_address = request.args.get("ipAddress")
    key = request.args.get("key")

    if (
        hostname is None
        or not hostname.strip()
        or ip_address is None
        or not ip_address.strip()
        or key is None
        or not key.strip()
    ):
        return "hostname, ipAddress, and key are required", 400

    try:
        host, domain = parse_hostname(hostname)
    except ValueError as error:
        return str(error), 400

    try:
        upstream = requests.get(
            NAMECHEAP_UPDATE_URL,
            params={
                "host": host,
                "domain": domain,
                "password": key,
                "ip": ip_address,
            },
            timeout=UPSTREAM_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        return "Namecheap request failed", 502

    response = make_response(upstream.text, upstream.status_code)
    content_type = upstream.headers.get("Content-Type")
    if content_type:
        response.headers["Content-Type"] = content_type
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
