from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import requests

from app import app


SUCCESS_XML = (
    '<?xml version="1.0" encoding="utf-8"?>'
    "<interface-response><ErrCount>0</ErrCount></interface-response>"
)


class UpdateDnsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True

    def setUp(self):
        self.client = app.test_client()

    @patch("app.requests.get")
    def test_supports_legacy_parameter_names(self, get):
        get.return_value = SimpleNamespace(
            text=SUCCESS_XML,
            status_code=200,
            headers={"Content-Type": "text/xml"},
        )

        with self.assertLogs("app", level="INFO") as logs:
            response = self.client.get(
                "/update",
                query_string={
                    "hostname": "home.example.com",
                    "ipAddress": "192.0.2.10",
                    "key": "secret",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "good")
        self.assertEqual(response.mimetype, "text/plain")
        self.assertTrue(any("source=hostname" in message for message in logs.output))
        self.assertNotIn("secret", logs.output)
        get.assert_called_once_with(
            "https://dynamicdns.park-your-domain.com/update",
            params={
                "host": "home",
                "domain": "example.com",
                "password": "secret",
                "ip": "192.0.2.10",
            },
            timeout=10,
        )

    @patch("app.requests.get")
    def test_supports_synology_parameter_names_on_update_route(self, get):
        get.return_value = SimpleNamespace(
            text=SUCCESS_XML,
            status_code=200,
            headers={},
        )

        response = self.client.get(
            "/update",
            query_string={
                "host": "@",
                "domain": "example.com",
                "password": "secret",
                "ip": "192.0.2.10",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "good")
        get.assert_called_once_with(
            "https://dynamicdns.park-your-domain.com/update",
            params={
                "host": "@",
                "domain": "example.com",
                "password": "secret",
                "ip": "192.0.2.10",
            },
            timeout=10,
        )

    @patch("app.requests.get")
    def test_supports_synology_username_and_hostname_parameters(self, get):
        get.return_value = SimpleNamespace(
            text=SUCCESS_XML,
            status_code=200,
            headers={},
        )

        response = self.client.get(
            "/update",
            query_string={
                "username": "home",
                "hostname": "example.com",
                "password": "secret",
                "myip": "192.0.2.10",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "good")
        self.assertEqual(get.call_args.kwargs["params"]["host"], "home")
        self.assertEqual(get.call_args.kwargs["params"]["domain"], "example.com")
        self.assertEqual(get.call_args.kwargs["params"]["ip"], "192.0.2.10")

    @patch("app.requests.get")
    def test_returns_badauth_for_missing_parameters_with_http_200(self, get):
        response = self.client.get(
            "/update",
            query_string={
                "host": "home",
                "domain": "example.com",
                "ip": "192.0.2.10",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "badauth")
        get.assert_not_called()

    @patch("app.requests.get")
    def test_returns_nohost_for_invalid_legacy_hostname_with_http_200(self, get):
        response = self.client.get(
            "/update",
            query_string={
                "hostname": "localhost",
                "ipAddress": "192.0.2.10",
                "key": "secret",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "nohost")
        get.assert_not_called()

    @patch("app.requests.get")
    def test_maps_namecheap_errors_to_synology_responses(self, get):
        cases = (
            ("Domain name not found", "nohost"),
            ("Passwords do not match", "badauth"),
            ("No Records updated. A record not Found;", "nohost"),
            ("Unexpected Namecheap error", "911"),
        )

        for error_message, expected_response in cases:
            with self.subTest(error_message=error_message):
                get.return_value = SimpleNamespace(
                    text=(
                        "<interface-response><ErrCount>1</ErrCount>"
                        f"<errors><Err1>{error_message}</Err1></errors>"
                        "</interface-response>"
                    ),
                    status_code=200,
                    headers={},
                )

                response = self.client.get(
                    "/update",
                    query_string={
                        "host": "home",
                        "domain": "example.com",
                        "password": "secret",
                        "ip": "192.0.2.10",
                    },
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.text, expected_response)

    @patch("app.requests.get")
    def test_returns_911_for_upstream_failures_and_invalid_responses(self, get):
        for upstream_result in (
            requests.Timeout(),
            requests.ConnectionError(),
            SimpleNamespace(text="not xml", status_code=200, headers={}),
            SimpleNamespace(text=SUCCESS_XML, status_code=503, headers={}),
        ):
            with self.subTest(upstream_result=type(upstream_result).__name__):
                if isinstance(upstream_result, Exception):
                    get.side_effect = upstream_result
                else:
                    get.side_effect = None
                    get.return_value = upstream_result

                response = self.client.get(
                    "/update",
                    query_string={
                        "host": "home",
                        "domain": "example.com",
                        "password": "secret",
                        "ip": "192.0.2.10",
                    },
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.text, "911")

    @patch("app.requests.get")
    def test_does_not_log_the_password(self, get):
        get.return_value = SimpleNamespace(
            text=SUCCESS_XML,
            status_code=200,
            headers={},
        )

        with self.assertLogs("app", level="INFO") as logs:
            self.client.get(
                "/update",
                query_string={
                    "host": "home",
                    "domain": "example.com",
                    "password": "secret",
                    "ip": "192.0.2.10",
                },
            )

        self.assertNotIn("secret", logs.output)
