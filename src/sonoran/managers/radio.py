from __future__ import print_function

import json
import urllib.error
import urllib.parse
import urllib.request

from sonoran.models import CADStandardResponse


class RadioManager(object):
    def __init__(self, instance):
        self.instance = instance

    def _resolve_radio_server_id(self, server_id):
        resolved = server_id if server_id is not None else self.instance.radioDefaultServerId
        if not isinstance(resolved, int) or resolved <= 0:
            raise ValueError("serverId must be a positive integer.")
        return resolved

    def _build_url(self, path):
        return "{0}/{1}".format(self.instance.radioApiUrl.rstrip("/"), path.lstrip("/"))

    def _parse_response_payload(self, payload):
        if not payload:
            return None
        text = payload.decode("utf-8")
        if not text.strip():
            return None
        try:
            return json.loads(text)
        except ValueError:
            return text

    def _request(self, method, path, body=None, authenticated=True):
        headers = {"Accept": "application/json"}
        headers.update(self.instance.apiHeaders)
        if authenticated:
            if not self.instance.radioApiKey:
                raise ValueError("radioApiKey is required for authenticated Radio requests.")
            headers["Authorization"] = "Bearer {0}".format(self.instance.radioApiKey)

        payload = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            payload = json.dumps(body).encode("utf-8")

        request = urllib.request.Request(self._build_url(path), data=payload, headers=dict(headers), method=method.upper())
        try:
            with urllib.request.urlopen(request, timeout=self.instance.timeout) as response:
                return CADStandardResponse(success=True, data=self._parse_response_payload(response.read()))
        except urllib.error.HTTPError as error:
            return CADStandardResponse(success=False, reason=self._parse_response_payload(error.read()))

    def getCommunityChannelsV2(self, serverId=None):
        resolved_server_id = self._resolve_radio_server_id(serverId)
        return self._request("GET", "v2/servers/{0}/channels".format(resolved_server_id))

    def getConnectedUsersV2(self, serverId=None):
        resolved_server_id = self._resolve_radio_server_id(serverId)
        return self._request("GET", "v2/servers/{0}/connected-users".format(resolved_server_id))

    def getConnectedUserV2(self, roomId, identity, serverId=None):
        resolved_server_id = self._resolve_radio_server_id(serverId)
        return self._request("GET", "v2/servers/{0}/rooms/{1}/users/{2}".format(
            resolved_server_id,
            int(roomId),
            urllib.parse.quote(identity, safe=""),
        ))

    def setUserChannelsV2(self, roomId, identity, options=None, serverId=None):
        resolved_server_id = self._resolve_radio_server_id(serverId)
        return self._request(
            "PATCH",
            "v2/servers/{0}/rooms/{1}/users/{2}/channels".format(
                resolved_server_id,
                int(roomId),
                urllib.parse.quote(identity, safe=""),
            ),
            body=dict(options or {}),
        )

    def setUserDisplayNameV2(self, data):
        resolved_server_id = self._resolve_radio_server_id(data.get("serverId"))
        payload = dict(data)
        payload.pop("serverId", None)
        return self._request("PATCH", "v2/servers/{0}/users/display-name".format(resolved_server_id), body=payload)

    def approveMembersV2(self, accIds, serverId=None):
        resolved_server_id = self._resolve_radio_server_id(serverId)
        return self._request("POST", "v2/servers/{0}/members/approve".format(resolved_server_id), body={"accIds": list(accIds)})

    def kickMembersV2(self, accIds, serverId=None):
        resolved_server_id = self._resolve_radio_server_id(serverId)
        return self._request("POST", "v2/servers/{0}/members/kick".format(resolved_server_id), body={"accIds": list(accIds)})

    def banMembersV2(self, accIds, serverId=None):
        resolved_server_id = self._resolve_radio_server_id(serverId)
        return self._request("POST", "v2/servers/{0}/members/ban".format(resolved_server_id), body={"accIds": list(accIds)})

    def setMemberDisplayNamesV2(self, accNicknames, serverId=None):
        resolved_server_id = self._resolve_radio_server_id(serverId)
        return self._request("PATCH", "v2/servers/{0}/members/display-names".format(resolved_server_id), body={"accNicknames": list(accNicknames)})

    def setMemberPermissionsV2(self, userPerms, serverId=None):
        resolved_server_id = self._resolve_radio_server_id(serverId)
        return self._request("PATCH", "v2/servers/{0}/members/permissions".format(resolved_server_id), body={"userPerms": list(userPerms)})

    def getServerSubscriptionFromIpV2(self):
        return self._request("GET", "v2/server-subscriptions/by-ip", authenticated=False)

    def setServerIpV2(self, data):
        resolved_server_id = self._resolve_radio_server_id(data.get("serverId"))
        payload = dict(data)
        payload.pop("serverId", None)
        return self._request("POST", "v2/servers/{0}/server-ip".format(resolved_server_id), body=payload)

    def setInGameSpeakerLocationsV2(self, locations, serverId=None):
        resolved_server_id = self._resolve_radio_server_id(serverId)
        return self._request("PUT", "v2/servers/{0}/speakers".format(resolved_server_id), body={"locations": list(locations)})

    def playToneV2(self, roomId, tones, playTo, serverId=None):
        resolved_server_id = self._resolve_radio_server_id(serverId)
        return self._request("POST", "v2/servers/{0}/tones/play".format(resolved_server_id), body={
            "roomId": int(roomId),
            "tones": list(tones),
            "playTo": list(playTo),
        })
