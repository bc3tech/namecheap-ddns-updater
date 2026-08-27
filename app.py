import logging
import os
import sys
import xml.etree.ElementTree as ET

import flask
import requests
from azure.monitor.opentelemetry import configure_azure_monitor


NAMECHEAP_UPDATE_URL = "https://dynamicdns.park-your-domain.com/update"
UPSTREAM_TIMEOUT_SECONDS = 10

if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    configure_azure_monitor(logger_name=__name__)

app = flask.Flask(__name__)
app.logger.setLevel(logging.INFO)
if not any(isinstance(handler, logging.StreamHandler) for handler in app.logger.handlers):
    app.logger.addHandler(logging.StreamHandler(sys.stderr))
app.logger.propagate = False


def parse_hostname(hostname: str) -> tuple[str, str]:
    labels = hostname.strip().rstrip(".").split(".")
    if len(labels) < 2 or any(not label for label in labels):
        raise ValueError("hostname must include a domain and suffix")

    domain = ".".join(labels[-2:])
    host = ".".join(labels[:-2]) or "@"
    return host, domain


def validate_domain(domain: str) -> str:
    normalized = domain.strip().rstrip(".")
    labels = normalized.split(".")
    if len(labels) < 2 or any(not label for label in labels):
        raise ValueError("domain must include a domain and suffix")
    return normalized


def resolve_update_parameters() -> tuple[str, str | None, str | None, str | None, str | None]:
    args = flask.request.args
    ip_address = args.get("ip") or args.get("myip") or args.get("ipAddress")
    key = args.get("password") or args.get("key")

    if args.get("host") is not None or args.get("domain") is not None:
        return (
            "synology-split",
            args.get("host") or args.get("username"),
            args.get("domain"),
            key,
            ip_address,
        )

    if args.get("username") is not None and args.get("hostname") is not None:
        return (
            "synology-username",
            args.get("username"),
            args.get("hostname"),
            key,
            ip_address,
        )

    hostname = args.get("hostname")
    if hostname is None:
        return "hostname", None, None, key, ip_address
    return "hostname", hostname, None, key, ip_address


def protocol_response(body: str):
    response = flask.make_response(body, 200)
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


def xml_text(root: ET.Element, name: str) -> str | None:
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == name:
            return (element.text or "").strip()
    return None


def map_namecheap_response(response_text: str) -> tuple[str, str | None]:
    cleaned_response = response_text.strip().replace('encoding="utf-16"', "")
    root = ET.fromstring(cleaned_response)

    err_count_text = xml_text(root, "ErrCount")
    if err_count_text is None:
        raise ValueError("Namecheap response did not contain ErrCount")

    try:
        error_count = int(err_count_text)
    except ValueError as error:
        raise ValueError("Namecheap response contained an invalid ErrCount") from error

    if error_count == 0:
        return "good", None

    error_message = xml_text(root, "Err1")
    if not error_message:
        return "911", "Namecheap returned an error without details"

    normalized_error = " ".join(error_message.lower().split())
    if (
        "domain name not found" in normalized_error
        or "no records updated" in normalized_error
        and "record not found" in normalized_error
    ):
        return "nohost", error_message
    if "passwords do not match" in normalized_error:
        return "badauth", error_message
    return "911", error_message


@app.get("/update")
def update_dns():
    app.logger.info(
        "Received DDNS update request path=%s remote_addr=%s user_agent=%s "
        "query_parameters=%s",
        flask.request.path,
        flask.request.remote_addr or "-",
        flask.request.user_agent.string or "-",
        ",".join(sorted(flask.request.args.keys())) or "-",
    )

    source, host, domain, key, ip_address = resolve_update_parameters()
    app.logger.info(
        "Resolved DDNS parameters source=%s host=%s domain=%s ip=%s key_provided=%s",
        source,
        host,
        domain,
        ip_address,
        key is not None,
    )

    if source == "hostname":
        missing_parameter = (
            host is None
            or not host.strip()
            or ip_address is None
            or not ip_address.strip()
            or key is None
            or not key.strip()
        )
    else:
        missing_parameter = (
            host is None
            or not host.strip()
            or domain is None
            or not domain.strip()
            or ip_address is None
            or not ip_address.strip()
            or key is None
            or not key.strip()
        )

    if missing_parameter:
        app.logger.warning(
            "Rejecting request: missing or blank DDNS parameters source=%s",
            source,
        )
        return protocol_response("badauth")

    try:
        if source == "hostname":
            host, domain = parse_hostname(host)
        else:
            host = host.strip()
        domain = validate_domain(domain)
    except ValueError as error:
        app.logger.warning(
            "Rejecting request: invalid DDNS host/domain source=%s host=%s "
            "domain=%s error=%s",
            source,
            host,
            domain,
            str(error),
        )
        return protocol_response("nohost")

    ip_address = ip_address.strip()
    app.logger.info(
        "Validated DDNS parameters source=%s host=%s domain=%s ip=%s",
        source,
        host,
        domain,
        ip_address,
    )

    try:
        app.logger.info(
            "Sending request to Namecheap endpoint=%s host=%s domain=%s ip=%s",
            NAMECHEAP_UPDATE_URL,
            host,
            domain,
            ip_address,
        )
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
        app.logger.info(
            "Received response from Namecheap status_code=%s content_type=%s "
            "content_length=%s",
            upstream.status_code,
            upstream.headers.get("Content-Type", "-"),
            len(upstream.text),
        )
    except requests.Timeout:
        app.logger.error(
            "Namecheap request timed out source=%s host=%s domain=%s",
            source,
            host,
            domain,
        )
        return protocol_response("911")
    except requests.RequestException as error:
        app.logger.error(
            "Namecheap request failed source=%s host=%s domain=%s error_type=%s",
            source,
            host,
            domain,
            type(error).__name__,
        )
        return protocol_response("911")

    if not 200 <= upstream.status_code < 300:
        app.logger.error(
            "Namecheap returned an HTTP error status_code=%s source=%s host=%s "
            "domain=%s",
            upstream.status_code,
            source,
            host,
            domain,
        )
        return protocol_response("911")

    try:
        result, error_message = map_namecheap_response(upstream.text)
    except (ET.ParseError, ValueError) as error:
        app.logger.error(
            "Failed to interpret Namecheap response source=%s host=%s domain=%s "
            "error_type=%s error=%s",
            source,
            host,
            domain,
            type(error).__name__,
            str(error),
        )
        return protocol_response("911")

    if result == "good":
        app.logger.info(
            "Namecheap DNS update successful source=%s host=%s domain=%s ip=%s",
            source,
            host,
            domain,
            ip_address,
        )
    else:
        app.logger.warning(
            "Namecheap DNS update returned protocol_result=%s source=%s host=%s "
            "domain=%s error=%s",
            result,
            source,
            host,
            domain,
            error_message or "-",
        )

    return protocol_response(result if result != "911" else "911")


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "7780")),
    )
