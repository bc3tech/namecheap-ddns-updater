from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from app import app


class UpdateDnsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True

    def setUp(self):
        self.client = app.test_client()

    @patch("app.requests.get")
    def test_forwards_full_subdomain_and_returns_upstream_response(self, get):
        get.return_value = SimpleNamespace(
            text="good 1.2.3.4",
            status_code=200,
            headers={"Content-Type": "text/plain"},
        )

        response = self.client.get(
            "/update",
            query_string={
                "hostname": "home.example.com",
                "ipAddress": "192.0.2.10",
                "key": "secret",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "good 1.2.3.4")
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
    def test_preserves_nested_wildcard_and_apex_hosts(self, get):
        get.return_value = SimpleNamespace(
            text="ok",
            status_code=200,
            headers={},
        )

        for hostname, expected_host in (
            ("foo.bar.example.com", "foo.bar"),
            ("*.example.com", "*"),
            ("@.example.com", "@"),
        ):
            with self.subTest(hostname=hostname):
                response = self.client.get(
                    "/update",
                    query_string={
                        "hostname": hostname,
                        "ipAddress": "192.0.2.10",
                        "key": "secret",
                    },
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    get.call_args.kwargs["params"]["host"],
                    expected_host,
                )

    @patch("app.requests.get")
    def test_maps_root_domain_to_apex_host(self, get):
        get.return_value = SimpleNamespace(
            text="ok",
            status_code=200,
            headers={},
        )

        response = self.client.get(
            "/update",
            query_string={
                "hostname": "example.com",
                "ipAddress": "192.0.2.10",
                "key": "secret",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_args.kwargs["params"]["host"], "@")

    @patch("app.requests.get")
    def test_rejects_missing_or_blank_parameters_without_calling_upstream(self, get):
        for query_string in (
            {"ipAddress": "192.0.2.10", "key": "secret"},
            {"hostname": "example.com", "key": "secret"},
            {"hostname": "example.com", "ipAddress": "192.0.2.10"},
            {
                "hostname": " ",
                "ipAddress": "192.0.2.10",
                "key": "secret",
            },
        ):
            with self.subTest(query_string=query_string):
                response = self.client.get("/update", query_string=query_string)
                self.assertEqual(response.status_code, 400)

        get.assert_not_called()

    @patch("app.requests.get")
    def test_rejects_hostname_without_domain(self, get):
        response = self.client.get(
            "/update",
            query_string={
                "hostname": "localhost",
                "ipAddress": "192.0.2.10",
                "key": "secret",
            },
        )

        self.assertEqual(response.status_code, 400)
        get.assert_not_called()

    @patch("app.requests.get")
    def test_returns_bad_gateway_when_upstream_request_fails(self, get):
        import requests

        get.side_effect = requests.Timeout()

        response = self.client.get(
            "/update",
            query_string={
                "hostname": "example.com",
                "ipAddress": "192.0.2.10",
                "key": "secret",
            },
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.text, "Namecheap request failed")
