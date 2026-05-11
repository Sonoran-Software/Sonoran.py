from __future__ import print_function

import json
import urllib.error
import urllib.parse
import urllib.request

from sonoran.models import CADStandardResponse


class RadioManager(object):
    def __init__(self, instance):
        self.instance = instance

    def _resolve_radio_community_id(self, community_id=None):
        resolved = community_id
        if resolved is None:
            resolved = self.instance.radioCommunityId
        if isinstance(resolved, str):
            resolved = resolved.strip()
            if not resolved:
                raise ValueError("communityId is required.")
            return resolved
        if not isinstance(resolved, int) or resolved <= 0:
            raise ValueError("communityId must be a non-empty string or a positive integer.")
        return resolved

    def _resolve_radio_room_id(self):
        resolved = self.instance.radioRoomId
        if resolved is None:
            raise ValueError("roomId is required for Radio v2 room-scoped requests.")
        if not isinstance(resolved, int) or resolved <= 0:
            raise ValueError("roomId must be a positive integer.")
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

    def getCommunityChannelsV2(self, communityId=None):
        resolved_community_id = self._resolve_radio_community_id(communityId)
        return self._request("GET", "v2/servers/{0}/channels".format(resolved_community_id))

    def getConnectedUsersV2(self, communityId=None):
        resolved_community_id = self._resolve_radio_community_id(communityId)
        return self._request("GET", "v2/servers/{0}/connected-users".format(resolved_community_id))

    def getMembersV2(self, query=None, communityId=None):
        resolved_community_id = self._resolve_radio_community_id(communityId)
        query = dict(query or {})
        path = "v2/servers/{0}/members".format(resolved_community_id)
        if query:
            path = "{0}?{1}".format(path, urllib.parse.urlencode(query, doseq=True))
        return self._request("GET", path)

    def getConnectedUserV2(self, identity, communityId=None):
        resolved_community_id = self._resolve_radio_community_id(communityId)
        roomId = self._resolve_radio_room_id()
        return self._request("GET", "v2/servers/{0}/rooms/{1}/users/{2}".format(
            resolved_community_id,
            roomId,
            urllib.parse.quote(identity, safe=""),
        ))

    def setUserChannelsV2(self, identity, options=None, communityId=None):
        resolved_community_id = self._resolve_radio_community_id(communityId)
        roomId = self._resolve_radio_room_id()
        return self._request(
            "PATCH",
            "v2/servers/{0}/rooms/{1}/users/{2}/channels".format(
                resolved_community_id,
                roomId,
                urllib.parse.quote(identity, safe=""),
            ),
            body=dict(options or {}),
        )

    def setUserDisplayNameV2(self, data):
        resolved_community_id = self._resolve_radio_community_id(data.get("communityId"))
        payload = dict(data)
        payload.pop("serverId", None)
        payload.pop("communityId", None)
        return self._request("PATCH", "v2/servers/{0}/users/display-name".format(resolved_community_id), body=payload)

    def approveMembersV2(self, accIds, communityId=None):
        resolved_community_id = self._resolve_radio_community_id(communityId)
        return self._request("POST", "v2/servers/{0}/members/approve".format(resolved_community_id), body={"accIds": list(accIds)})

    def kickMembersV2(self, accIds, communityId=None):
        resolved_community_id = self._resolve_radio_community_id(communityId)
        return self._request("POST", "v2/servers/{0}/members/kick".format(resolved_community_id), body={"accIds": list(accIds)})

    def banMembersV2(self, accIds, communityId=None):
        resolved_community_id = self._resolve_radio_community_id(communityId)
        return self._request("POST", "v2/servers/{0}/members/ban".format(resolved_community_id), body={"accIds": list(accIds)})

    def setMemberDisplayNamesV2(self, accNicknames, communityId=None):
        resolved_community_id = self._resolve_radio_community_id(communityId)
        return self._request("PATCH", "v2/servers/{0}/members/display-names".format(resolved_community_id), body={"accNicknames": list(accNicknames)})

    def setMemberPermissionsV2(self, userPerms, communityId=None):
        resolved_community_id = self._resolve_radio_community_id(communityId)
        return self._request("PATCH", "v2/servers/{0}/members/permissions".format(resolved_community_id), body={"userPerms": list(userPerms)})

    def getServerSubscriptionFromIpV2(self):
        return self._request("GET", "v2/server-subscriptions/by-ip", authenticated=False)

    def setServerIpV2(self, data):
        resolved_community_id = self._resolve_radio_community_id(data.get("communityId"))
        payload = dict(data)
        payload.pop("serverId", None)
        payload.pop("communityId", None)
        payload["roomId"] = self._resolve_radio_room_id()
        return self._request("POST", "v2/servers/{0}/server-ip".format(resolved_community_id), body=payload)

    def setInGameSpeakerLocationsV2(self, locations, communityId=None):
        resolved_community_id = self._resolve_radio_community_id(communityId)
        return self._request("PUT", "v2/servers/{0}/speakers".format(resolved_community_id), body={"locations": list(locations)})

    def playToneV2(self, tones, playTo, communityId=None):
        resolved_community_id = self._resolve_radio_community_id(communityId)
        return self._request("POST", "v2/servers/{0}/tones/play".format(resolved_community_id), body={
            "roomId": self._resolve_radio_room_id(),
            "tones": list(tones),
            "playTo": list(playTo),
        })
