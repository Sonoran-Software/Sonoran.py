from __future__ import print_function

import io
import json
import unittest
import urllib.error

from unittest.mock import patch

from sonoran import Instance, productEnums


class FakeResponse(object):
    def __init__(self, payload=None):
        self.payload = payload

    def read(self):
        if self.payload is None:
            return b""
        if isinstance(self.payload, bytes):
            return self.payload
        if isinstance(self.payload, str):
            return self.payload.encode("utf-8")
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None


class CADV2Tests(unittest.TestCase):
    def setUp(self):
        self.instance = Instance(
            apiKey="test-key",
            communityId="test-community",
            product=productEnums.CAD,
            serverId=7,
        )
        self.assertIsNotNone(self.instance.cad)
        self.cad = self.instance.cad

    def test_get_login_page_v2_uses_public_request(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            return FakeResponse({"ok": True})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = self.cad.getLoginPageV2({"communityId": "public-community"})

        self.assertTrue(response.success)
        self.assertEqual(
            captured["url"],
            "https://api.sonorancad.com/v2/general/login-page?communityId=public-community",
        )
        self.assertNotIn("Authorization", captured["headers"])

    def test_get_calls_v2_builds_query_and_server_path(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            return FakeResponse({"calls": []})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = self.cad.getCallsV2({"serverId": 5, "closedLimit": 10, "type": "dispatch"})

        self.assertTrue(response.success)
        self.assertEqual(
            captured["url"],
            "https://api.sonorancad.com/v2/emergency/servers/5/calls?closedLimit=10&type=dispatch",
        )

    def test_create_emergency_call_v2_strips_server_id_from_body(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["method"] = request.get_method()
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse({"callId": 123})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = self.cad.createEmergencyCallV2(
                {
                    "serverId": 3,
                    "isEmergency": True,
                    "caller": "John Doe",
                    "location": "101 Alta Street",
                    "description": "Structure fire",
                }
            )

        self.assertTrue(response.success)
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(
            captured["url"],
            "https://api.sonorancad.com/v2/emergency/servers/3/calls/911",
        )
        self.assertNotIn("serverId", captured["body"])

    def test_add_identifiers_to_group_v2_uses_group_name_in_path(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse({"ok": True})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = self.cad.addIdentifiersToGroupV2(
                {
                    "serverId": 8,
                    "groupName": "CAR-51",
                    "apiIds": ["abc", "def"],
                }
            )

        self.assertTrue(response.success)
        self.assertEqual(
            captured["url"],
            "https://api.sonorancad.com/v2/emergency/servers/8/identifier-groups/CAR-51",
        )
        self.assertEqual(captured["body"], {"communityUserIds": ["abc", "def"]})

    def test_get_characters_v2_supports_roblox_query(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            return FakeResponse({"characters": []})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = self.cad.getCharactersV2({"roblox": 123456789})

        self.assertTrue(response.success)
        self.assertEqual(
            captured["url"],
            "https://api.sonorancad.com/v2/civilian/characters?roblox=123456789",
        )

    def test_kick_unit_v2_supports_roblox_body(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse({"ok": True})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = self.cad.kickUnitV2({"serverId": 4, "roblox": 123456789, "reason": "spam"})

        self.assertTrue(response.success)
        self.assertEqual(
            captured["url"],
            "https://api.sonorancad.com/v2/emergency/servers/4/units/kick",
        )
        self.assertEqual(captured["body"], {"roblox": 123456789, "reason": "spam"})

    def test_update_unit_locations_v2_supports_roblox_updates(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse({"updated": 1})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = self.cad.updateUnitLocationsV2(
                {
                    "serverId": 4,
                    "updates": [{"roblox": 123456789, "location": "Mission Row"}],
                }
            )

        self.assertTrue(response.success)
        self.assertEqual(
            captured["url"],
            "https://api.sonorancad.com/v2/emergency/servers/4/unit-locations",
        )
        self.assertEqual(captured["body"], {"updates": [{"roblox": 123456789, "location": "Mission Row"}]})

    def test_retries_429_responses(self):
        calls = {"count": 0}

        def fake_urlopen(request, timeout):
            calls["count"] += 1
            if calls["count"] == 1:
                raise urllib.error.HTTPError(
                    request.full_url,
                    429,
                    "Too Many Requests",
                    {"Retry-After": "0"},
                    io.BytesIO(json.dumps({"message": "slow down"}).encode("utf-8")),
                )
            return FakeResponse({"version": 2})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), patch("time.sleep") as sleep_mock:
            response = self.cad.getVersionV2()

        self.assertTrue(response.success)
        self.assertEqual(calls["count"], 2)
        sleep_mock.assert_called_once()

    def test_returns_plain_text_reason_on_failure(self):
        def fake_urlopen(request, timeout):
            raise urllib.error.HTTPError(
                request.full_url,
                500,
                "Internal Server Error",
                {},
                io.BytesIO(b"upstream failure"),
            )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = self.cad.verifySecretV2("bad-secret")

        self.assertFalse(response.success)
        self.assertEqual(response.reason, "upstream failure")

    def test_handles_empty_success_response(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            response = self.cad.removeRecordV2(42)

        self.assertTrue(response.success)
        self.assertIsNone(response.data)

    def test_create_record_v2_stringifies_replace_values(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse({"ok": True})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = self.cad.createRecordV2(
                {
                    "useDictionary": True,
                    "recordTypeId": 5,
                    "replaceValues": {
                        "year": 1990,
                        "status": True,
                        "flags": {"items": ["A", "B"]},
                        "skip": None,
                    },
                }
            )

        self.assertTrue(response.success)
        self.assertEqual(
            captured["body"]["replaceValues"],
            {
                "year": "1990",
                "status": "true",
                "flags": "{\"items\": [\"A\", \"B\"]}",
            },
        )


class RadioV2Tests(unittest.TestCase):
    def setUp(self):
        self.instance = Instance(
            apiKey="radio-key",
            communityId="radio-community",
            product=productEnums.RADIO,
            serverId=4,
        )
        self.assertIsNotNone(self.instance.radio)
        self.radio = self.instance.radio

    def test_get_connected_users_v2_uses_server_path(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            return FakeResponse({"connectedUsers": []})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = self.radio.getConnectedUsersV2()

        self.assertTrue(response.success)
        self.assertEqual(
            captured["url"],
            "https://api.sonoranradio.com/v2/servers/4/connected-users",
        )
        self.assertEqual(captured["headers"]["Authorization"], "Bearer radio-key")

    def test_set_server_ip_v2_strips_server_id_from_body(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse({"roomId": 2})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = self.radio.setServerIpV2(
                {
                    "serverId": 8,
                    "roomId": 2,
                    "serverPort": 30120,
                    "pushUrl": "http://127.0.0.1:30120/sonoranradio",
                }
            )

        self.assertTrue(response.success)
        self.assertEqual(
            captured["url"],
            "https://api.sonoranradio.com/v2/servers/8/server-ip",
        )
        self.assertNotIn("serverId", captured["body"])


if __name__ == "__main__":
    unittest.main()
