from __future__ import print_function

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from sonoran.models import CADStandardResponse

CAD_V2_RATE_LIMIT_MAX_RETRIES = 2
CAD_V2_RATE_LIMIT_DEFAULT_DELAY_MS = 1000
CAD_V2_RATE_LIMIT_MAX_DELAY_MS = 10000


class CADManager(object):
    def __init__(self, instance):
        self.instance = instance

    def _resolve_cad_server_id(self, server_id):
        resolved = server_id if server_id is not None else self.instance.cadDefaultServerId
        self._assert_positive_integer(resolved, "serverId")
        return int(resolved)

    def _assert_positive_integer(self, value, name):
        if not isinstance(value, int) or value <= 0:
            raise ValueError("{0} must be a positive integer.".format(name))

    def _without_keys(self, data, *keys):
        return dict((key, value) for key, value in data.items() if key not in keys)

    def _normalize_record_replace_values_body(self, data):
        body = dict(data)
        replace_values = body.get("replaceValues")
        if not isinstance(replace_values, dict):
            return body

        normalized = {}
        for key, value in replace_values.items():
            if value is None:
                continue
            if isinstance(value, str):
                normalized[key] = value
            elif isinstance(value, bool):
                normalized[key] = "true" if value else "false"
            elif isinstance(value, (int, float)):
                normalized[key] = str(value)
            else:
                normalized[key] = json.dumps(value)

        body["replaceValues"] = normalized
        return body

    def _build_url(self, path, query=None):
        base_url = self.instance.cadApiUrl.rstrip("/")
        url = "{0}/{1}".format(base_url, path.lstrip("/"))
        if query:
            parts = []
            for key, value in query.items():
                if value is None:
                    continue
                if isinstance(value, bool):
                    parts.append((key, "true" if value else "false"))
                elif isinstance(value, (list, tuple)):
                    for item in value:
                        if item is not None:
                            parts.append((key, str(item)))
                else:
                    parts.append((key, str(value)))
            if parts:
                url = "{0}?{1}".format(url, urllib.parse.urlencode(parts))
        return url

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

    def _resolve_retry_delay_ms(self, headers):
        if headers is None:
            return CAD_V2_RATE_LIMIT_DEFAULT_DELAY_MS

        retry_after = headers.get("Retry-After") if hasattr(headers, "get") else None
        if retry_after is None:
            return CAD_V2_RATE_LIMIT_DEFAULT_DELAY_MS

        try:
            retry_after_ms = int(float(retry_after) * 1000)
        except (TypeError, ValueError):
            return CAD_V2_RATE_LIMIT_DEFAULT_DELAY_MS

        if retry_after_ms <= 0:
            return CAD_V2_RATE_LIMIT_DEFAULT_DELAY_MS

        return min(retry_after_ms, CAD_V2_RATE_LIMIT_MAX_DELAY_MS)

    def _execute_cad_v2_request(self, method, path, query=None, body=None, authenticated=True):
        headers = {"Accept": "application/json"}
        headers.update(self.instance.apiHeaders)

        if authenticated:
            if not self.instance.cadApiKey:
                raise ValueError("cadApiKey is required for authenticated CAD requests.")
            headers["Authorization"] = "Bearer {0}".format(self.instance.cadApiKey)

        payload = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            payload = json.dumps(body).encode("utf-8")

        url = self._build_url(path, query)
        attempts = 0

        while True:
            request = urllib.request.Request(url, data=payload, headers=dict(headers), method=method.upper())
            try:
                with urllib.request.urlopen(request, timeout=self.instance.timeout) as response:
                    return CADStandardResponse(success=True, data=self._parse_response_payload(response.read()))
            except urllib.error.HTTPError as error:
                if error.code == 429 and attempts < CAD_V2_RATE_LIMIT_MAX_RETRIES:
                    attempts += 1
                    delay_ms = self._resolve_retry_delay_ms(error.headers)
                    time.sleep(delay_ms / 1000.0)
                    continue

                return CADStandardResponse(success=False, reason=self._parse_response_payload(error.read()))

    def getLoginPageV2(self, params=None):
        query = dict(params or {})
        query.setdefault("communityId", self.instance.cadCommunityId)
        return self._execute_cad_v2_request("GET", "v2/general/login-page", query=query, authenticated=False)

    def checkApiIdV2(self, apiId):
        return self._execute_cad_v2_request("GET", "v2/general/api-ids/{0}".format(urllib.parse.quote(apiId, safe="")))

    def applyPermissionKeyV2(self, data):
        return self._execute_cad_v2_request("POST", "v2/general/permission-keys/applications", body=dict(data))

    def banUserV2(self, data):
        return self._execute_cad_v2_request("POST", "v2/general/account-bans", body=dict(data))

    def setPenalCodesV2(self, codes):
        return self._execute_cad_v2_request("PUT", "v2/general/penal-codes", body={"codes": list(codes)})

    def setApiIdsV2(self, data):
        return self._execute_cad_v2_request("PUT", "v2/general/api-ids", body=dict(data))

    def getTemplatesV2(self, recordTypeId=None):
        if recordTypeId is not None:
            self._assert_positive_integer(recordTypeId, "recordTypeId")
            return self._execute_cad_v2_request("GET", "v2/general/templates/{0}".format(recordTypeId))
        return self._execute_cad_v2_request("GET", "v2/general/templates")

    def createRecordV2(self, data):
        return self._execute_cad_v2_request("POST", "v2/general/records", body=self._normalize_record_replace_values_body(data))

    def updateRecordV2(self, recordId, data):
        self._assert_positive_integer(recordId, "recordId")
        return self._execute_cad_v2_request("PATCH", "v2/general/records/{0}".format(recordId), body=self._normalize_record_replace_values_body(data))

    def removeRecordV2(self, recordId):
        self._assert_positive_integer(recordId, "recordId")
        return self._execute_cad_v2_request("DELETE", "v2/general/records/{0}".format(recordId))

    def sendRecordDraftV2(self, data):
        return self._execute_cad_v2_request("POST", "v2/general/record-drafts", body=self._normalize_record_replace_values_body(data))

    def lookupV2(self, data):
        return self._execute_cad_v2_request("POST", "v2/general/lookups", body=dict(data))

    def lookupByValueV2(self, data):
        return self._execute_cad_v2_request("POST", "v2/general/lookups/by-value", body=dict(data))

    def lookupCustomV2(self, data):
        return self._execute_cad_v2_request("POST", "v2/general/lookups/custom", body=dict(data))

    def getAccountV2(self, query=None):
        return self._execute_cad_v2_request("GET", "v2/general/accounts/account", query=dict(query or {}))

    def getAccountsV2(self, query=None):
        return self._execute_cad_v2_request("GET", "v2/general/accounts", query=dict(query or {}))

    def createCommunityLinkV2(self, data):
        return self._execute_cad_v2_request("POST", "v2/general/links", body=dict(data))

    def checkCommunityLinkV2(self, data):
        return self._execute_cad_v2_request("POST", "v2/general/links/check", body=dict(data))

    def setAccountPermissionsV2(self, data):
        return self._execute_cad_v2_request("PATCH", "v2/general/accounts/permissions", body=dict(data))

    def heartbeatV2(self, serverId, playerCount):
        resolved_server_id = self._resolve_cad_server_id(serverId)
        return self._execute_cad_v2_request("POST", "v2/general/servers/{0}/heartbeat".format(resolved_server_id), body={"playerCount": playerCount})

    def getVersionV2(self):
        return self._execute_cad_v2_request("GET", "v2/general/version")

    def getServersV2(self):
        return self._execute_cad_v2_request("GET", "v2/general/servers")

    def setServersV2(self, servers, deployMap=False):
        return self._execute_cad_v2_request("PUT", "v2/general/servers", body={"servers": list(servers), "deployMap": deployMap})

    def verifySecretV2(self, secret):
        return self._execute_cad_v2_request("POST", "v2/general/secrets/verify", body={"secret": secret})

    def authorizeStreetSignsV2(self, serverId=None):
        resolved_server_id = self._resolve_cad_server_id(serverId)
        return self._execute_cad_v2_request("POST", "v2/general/servers/{0}/street-sign-auth".format(resolved_server_id))

    def setPostalsV2(self, postals):
        return self._execute_cad_v2_request("PUT", "v2/general/postals", body={"postals": list(postals)})

    def sendPhotoV2(self, data):
        return self._execute_cad_v2_request("POST", "v2/general/photos", body=dict(data))

    def getInfoV2(self):
        return self._execute_cad_v2_request("GET", "v2/general/info")

    def getCharactersV2(self, query=None):
        return self._execute_cad_v2_request("GET", "v2/civilian/characters", query=dict(query or {}))

    def removeCharacterV2(self, characterId):
        self._assert_positive_integer(characterId, "characterId")
        return self._execute_cad_v2_request("DELETE", "v2/civilian/characters/{0}".format(characterId))

    def setSelectedCharacterV2(self, data):
        return self._execute_cad_v2_request("PUT", "v2/civilian/selected-character", body=dict(data))

    def getCharacterLinksV2(self, query=None):
        return self._execute_cad_v2_request("GET", "v2/civilian/character-links", query=dict(query or {}))

    def addCharacterLinkV2(self, syncId, data):
        return self._execute_cad_v2_request("PUT", "v2/civilian/character-links/{0}".format(urllib.parse.quote(syncId, safe="")), body=dict(data))

    def removeCharacterLinkV2(self, syncId, data):
        return self._execute_cad_v2_request("DELETE", "v2/civilian/character-links/{0}".format(urllib.parse.quote(syncId, safe="")), body=dict(data))

    def getUnitsV2(self, query=None):
        payload = dict(query or {})
        resolved_server_id = self._resolve_cad_server_id(payload.pop("serverId", None))
        return self._execute_cad_v2_request("GET", "v2/emergency/servers/{0}/units".format(resolved_server_id), query=payload)

    def getCallsV2(self, query=None):
        payload = dict(query or {})
        resolved_server_id = self._resolve_cad_server_id(payload.pop("serverId", None))
        return self._execute_cad_v2_request("GET", "v2/emergency/servers/{0}/calls".format(resolved_server_id), query=payload)

    def getCurrentCallV2(self, accountUuid):
        return self._execute_cad_v2_request("GET", "v2/emergency/accounts/{0}/current-call".format(urllib.parse.quote(accountUuid, safe="")))

    def updateUnitLocationsV2(self, data):
        payload = dict(data)
        resolved_server_id = self._resolve_cad_server_id(payload.pop("serverId", None))
        return self._execute_cad_v2_request("PATCH", "v2/emergency/servers/{0}/unit-locations".format(resolved_server_id), body=payload)

    def setUnitPanicV2(self, data):
        payload = dict(data)
        resolved_server_id = self._resolve_cad_server_id(payload.pop("serverId", None))
        return self._execute_cad_v2_request("PATCH", "v2/emergency/servers/{0}/units/panic".format(resolved_server_id), body=payload)

    def setUnitStatusV2(self, data):
        payload = dict(data)
        resolved_server_id = self._resolve_cad_server_id(payload.pop("serverId", None))
        return self._execute_cad_v2_request("PATCH", "v2/emergency/servers/{0}/units/status".format(resolved_server_id), body=payload)

    def kickUnitV2(self, data):
        payload = dict(data)
        resolved_server_id = self._resolve_cad_server_id(payload.pop("serverId", None))
        return self._execute_cad_v2_request("DELETE", "v2/emergency/servers/{0}/units/kick".format(resolved_server_id), body=payload)

    def getIdentifiersV2(self, accountUuid):
        return self._execute_cad_v2_request("GET", "v2/emergency/accounts/{0}/identifiers".format(urllib.parse.quote(accountUuid, safe="")))

    def getAccountUnitsV2(self, data):
        payload = dict(data)
        resolved_server_id = self._resolve_cad_server_id(payload.pop("serverId", None))
        account_uuid = urllib.parse.quote(str(payload.pop("accountUuid")), safe="")
        return self._execute_cad_v2_request("GET", "v2/emergency/servers/{0}/accounts/{1}/units".format(resolved_server_id, account_uuid), query=payload)

    def selectIdentifierV2(self, accountUuid, identId):
        return self._execute_cad_v2_request("PUT", "v2/emergency/accounts/{0}/selected-identifier".format(urllib.parse.quote(accountUuid, safe="")), body={"identId": identId})

    def createIdentifierV2(self, accountUuid, data):
        return self._execute_cad_v2_request("POST", "v2/emergency/accounts/{0}/identifiers".format(urllib.parse.quote(accountUuid, safe="")), body=dict(data))

    def updateIdentifierV2(self, accountUuid, identId, data):
        self._assert_positive_integer(identId, "identId")
        return self._execute_cad_v2_request("PATCH", "v2/emergency/accounts/{0}/identifiers/{1}".format(urllib.parse.quote(accountUuid, safe=""), identId), body=dict(data))

    def deleteIdentifierV2(self, accountUuid, identId):
        self._assert_positive_integer(identId, "identId")
        return self._execute_cad_v2_request("DELETE", "v2/emergency/accounts/{0}/identifiers/{1}".format(urllib.parse.quote(accountUuid, safe=""), identId))

    def addIdentifiersToGroupV2(self, data):
        payload = dict(data)
        resolved_server_id = self._resolve_cad_server_id(payload.pop("serverId", None))
        group_name = urllib.parse.quote(str(payload.pop("groupName")), safe="")
        return self._execute_cad_v2_request("PUT", "v2/emergency/servers/{0}/identifier-groups/{1}".format(resolved_server_id, group_name), body=payload)

    def createEmergencyCallV2(self, data):
        payload = dict(data)
        resolved_server_id = self._resolve_cad_server_id(payload.pop("serverId", None))
        return self._execute_cad_v2_request("POST", "v2/emergency/servers/{0}/calls/911".format(resolved_server_id), body=payload)

    def deleteEmergencyCallV2(self, callId, serverId=None):
        resolved_server_id = self._resolve_cad_server_id(serverId)
        self._assert_positive_integer(callId, "callId")
        return self._execute_cad_v2_request("DELETE", "v2/emergency/servers/{0}/calls/911/{1}".format(resolved_server_id, callId))

    def createDispatchCallV2(self, data):
        payload = dict(data)
        resolved_server_id = self._resolve_cad_server_id(payload.pop("serverId", None))
        return self._execute_cad_v2_request("POST", "v2/emergency/servers/{0}/dispatch-calls".format(resolved_server_id), body=payload)

    def updateDispatchCallV2(self, callId, data):
        resolved_server_id = self._resolve_cad_server_id(data.get("serverId"))
        self._assert_positive_integer(callId, "callId")
        return self._execute_cad_v2_request("PATCH", "v2/emergency/servers/{0}/dispatch-calls/{1}".format(resolved_server_id, callId), body=self._without_keys(data, "serverId"))

    def attachUnitsToDispatchCallV2(self, callId, data):
        resolved_server_id = self._resolve_cad_server_id(data.get("serverId"))
        self._assert_positive_integer(callId, "callId")
        return self._execute_cad_v2_request("POST", "v2/emergency/servers/{0}/dispatch-calls/{1}/attachments".format(resolved_server_id, callId), body=self._without_keys(data, "serverId"))

    def detachUnitsFromDispatchCallV2(self, data):
        resolved_server_id = self._resolve_cad_server_id(data.get("serverId"))
        return self._execute_cad_v2_request("DELETE", "v2/emergency/servers/{0}/dispatch-calls/attachments".format(resolved_server_id), body=self._without_keys(data, "serverId"))

    def setDispatchPostalV2(self, callId, postal, serverId=None):
        resolved_server_id = self._resolve_cad_server_id(serverId)
        self._assert_positive_integer(callId, "callId")
        return self._execute_cad_v2_request("PATCH", "v2/emergency/servers/{0}/dispatch-calls/{1}/postal".format(resolved_server_id, callId), body={"postal": postal})

    def setDispatchPrimaryV2(self, callId, identId, trackPrimary=False, serverId=None):
        resolved_server_id = self._resolve_cad_server_id(serverId)
        self._assert_positive_integer(callId, "callId")
        self._assert_positive_integer(identId, "identId")
        return self._execute_cad_v2_request("PATCH", "v2/emergency/servers/{0}/dispatch-calls/{1}/primary".format(resolved_server_id, callId), body={"identId": identId, "trackPrimary": trackPrimary})

    def addDispatchNoteV2(self, callId, data):
        resolved_server_id = self._resolve_cad_server_id(data.get("serverId"))
        self._assert_positive_integer(callId, "callId")
        return self._execute_cad_v2_request("POST", "v2/emergency/servers/{0}/dispatch-calls/{1}/notes".format(resolved_server_id, callId), body=self._without_keys(data, "serverId"))

    def closeDispatchCallsV2(self, callIds, serverId=None):
        resolved_server_id = self._resolve_cad_server_id(serverId)
        return self._execute_cad_v2_request("POST", "v2/emergency/servers/{0}/dispatch-calls/close".format(resolved_server_id), body={"callIds": list(callIds)})

    def updateStreetSignsV2(self, data):
        resolved_server_id = self._resolve_cad_server_id(data.get("serverId"))
        return self._execute_cad_v2_request("PATCH", "v2/emergency/servers/{0}/street-signs".format(resolved_server_id), body=self._without_keys(data, "serverId"))

    def setStreetSignConfigV2(self, signs, serverId=None):
        resolved_server_id = self._resolve_cad_server_id(serverId)
        return self._execute_cad_v2_request("PUT", "v2/emergency/servers/{0}/street-sign-config".format(resolved_server_id), body={"signs": list(signs)})

    def setAvailableCalloutsV2(self, callouts, serverId=None):
        resolved_server_id = self._resolve_cad_server_id(serverId)
        return self._execute_cad_v2_request("PUT", "v2/emergency/servers/{0}/callouts".format(resolved_server_id), body={"callouts": list(callouts)})

    def getPagerConfigV2(self, serverId=None):
        resolved_server_id = self._resolve_cad_server_id(serverId)
        return self._execute_cad_v2_request("GET", "v2/emergency/servers/{0}/pager-config".format(resolved_server_id))

    def setPagerConfigV2(self, data):
        resolved_server_id = self._resolve_cad_server_id(data.get("serverId"))
        return self._execute_cad_v2_request("PUT", "v2/emergency/servers/{0}/pager-config".format(resolved_server_id), body=self._without_keys(data, "serverId"))

    def setStationsV2(self, config, serverId=None):
        resolved_server_id = self._resolve_cad_server_id(serverId)
        return self._execute_cad_v2_request("PUT", "v2/emergency/servers/{0}/stations".format(resolved_server_id), body={"config": config})

    def getBlipsV2(self, serverId=None):
        resolved_server_id = self._resolve_cad_server_id(serverId)
        return self._execute_cad_v2_request("GET", "v2/emergency/servers/{0}/blips".format(resolved_server_id))

    def createBlipV2(self, data):
        resolved_server_id = self._resolve_cad_server_id(data.get("serverId"))
        return self._execute_cad_v2_request("POST", "v2/emergency/servers/{0}/blips".format(resolved_server_id), body=self._without_keys(data, "serverId"))

    def updateBlipV2(self, blipId, data):
        resolved_server_id = self._resolve_cad_server_id(data.get("serverId"))
        self._assert_positive_integer(blipId, "blipId")
        return self._execute_cad_v2_request("PATCH", "v2/emergency/servers/{0}/blips/{1}".format(resolved_server_id, blipId), body=self._without_keys(data, "serverId"))

    def deleteBlipsV2(self, ids, serverId=None):
        resolved_server_id = self._resolve_cad_server_id(serverId)
        return self._execute_cad_v2_request("POST", "v2/emergency/servers/{0}/blips/delete".format(resolved_server_id), body={"ids": list(ids)})
