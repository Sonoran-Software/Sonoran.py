from __future__ import print_function

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from sonoran.models import CADStandardResponse

CMS_V2_RATE_LIMIT_MAX_RETRIES = 2
CMS_V2_RATE_LIMIT_DEFAULT_DELAY_MS = 1000
CMS_V2_RATE_LIMIT_MAX_DELAY_MS = 10000


class CMSManager(object):
    def __init__(self, instance):
        self.instance = instance

    def _resolve_cms_server_id(self, server_id):
        resolved = server_id if server_id is not None else self.instance.cmsDefaultServerId
        self._assert_positive_integer(resolved, "serverId")
        return int(resolved)

    def _assert_positive_integer(self, value, name):
        if not isinstance(value, int) or value <= 0:
            raise ValueError("{0} must be a positive integer.".format(name))

    def _without_keys(self, data, *keys):
        return dict((key, value) for key, value in data.items() if key not in keys)

    def _build_url(self, path, query=None):
        base_url = self.instance.cmsApiUrl.rstrip("/")
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
            return CMS_V2_RATE_LIMIT_DEFAULT_DELAY_MS

        retry_after = headers.get("Retry-After") if hasattr(headers, "get") else None
        if retry_after is None:
            return CMS_V2_RATE_LIMIT_DEFAULT_DELAY_MS

        try:
            retry_after_ms = int(float(retry_after) * 1000)
        except (TypeError, ValueError):
            return CMS_V2_RATE_LIMIT_DEFAULT_DELAY_MS

        if retry_after_ms <= 0:
            return CMS_V2_RATE_LIMIT_DEFAULT_DELAY_MS

        return min(retry_after_ms, CMS_V2_RATE_LIMIT_MAX_DELAY_MS)

    def _execute_cms_v2_request(self, method, path, query=None, body=None, authenticated=True):
        headers = {"Accept": "application/json"}
        headers.update(self.instance.apiHeaders)

        if authenticated:
            if not self.instance.cmsApiKey:
                raise ValueError("cmsApiKey is required for authenticated CMS requests.")
            headers["Authorization"] = "Bearer {0}".format(self.instance.cmsApiKey)

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
                if error.code == 429 and attempts < CMS_V2_RATE_LIMIT_MAX_RETRIES:
                    attempts += 1
                    delay_ms = self._resolve_retry_delay_ms(error.headers)
                    time.sleep(delay_ms / 1000.0)
                    continue

                return CADStandardResponse(success=False, reason=self._parse_response_payload(error.read()))

    def getCommunityV2(self):
        return self._execute_cms_v2_request("GET", "v2/community")

    def getSubVersionV2(self):
        return self._execute_cms_v2_request("GET", "v2/community/sub-version")

    def lookupCommunityV2(self, query=None):
        return self._execute_cms_v2_request("GET", "v2/community/lookup", query=dict(query or {}))

    def getDepartmentsV2(self):
        return self._execute_cms_v2_request("GET", "v2/community/departments")

    def getProfileFieldsV2(self):
        return self._execute_cms_v2_request("GET", "v2/community/profile-fields")

    def getClockInTypesV2(self):
        return self._execute_cms_v2_request("GET", "v2/community/clockin-types")

    def getCustomLogTypesV2(self):
        return self._execute_cms_v2_request("GET", "v2/community/custom-log-types")

    def getPromotionFlowsV2(self):
        return self._execute_cms_v2_request("GET", "v2/community/promotion-flows")

    def triggerPromotionFlowsV2(self, data):
        return self._execute_cms_v2_request("POST", "v2/community/promotion-flows/trigger", body=dict(data))

    def undoRankChangeV2(self, undo_id, data=None):
        self._assert_positive_integer(undo_id, "undoId")
        return self._execute_cms_v2_request("POST", "v2/community/rank-changes/{0}/undo".format(undo_id), body=dict(data or {}))

    def createShortUrlV2(self, data):
        return self._execute_cms_v2_request("POST", "v2/community/short-urls", body=dict(data))

    def getAccountsV2(self, query=None):
        return self._execute_cms_v2_request("GET", "v2/community/accounts", query=dict(query or {}))

    def searchAccountsV2(self, query=None):
        return self._execute_cms_v2_request("GET", "v2/community/accounts/search", query=dict(query or {}))

    def getAccountV2(self, account_id):
        return self._execute_cms_v2_request("GET", "v2/community/accounts/{0}".format(urllib.parse.quote(str(account_id), safe="")))

    def getAccountRanksV2(self, account_id):
        return self._execute_cms_v2_request("GET", "v2/community/accounts/{0}/ranks".format(urllib.parse.quote(str(account_id), safe="")))

    def getAccountIdentifiersV2(self, account_id):
        return self._execute_cms_v2_request("GET", "v2/community/accounts/{0}/identifiers".format(urllib.parse.quote(str(account_id), safe="")))

    def registerAccountIdentifiersV2(self, account_id, data):
        return self._execute_cms_v2_request("POST", "v2/community/accounts/{0}/identifiers".format(urllib.parse.quote(str(account_id), safe="")), body=dict(data))

    def setAccountNameV2(self, account_id, data):
        return self._execute_cms_v2_request("PATCH", "v2/community/accounts/{0}/name".format(urllib.parse.quote(str(account_id), safe="")), body=dict(data))

    def setAccountRanksV2(self, account_id, data):
        return self._execute_cms_v2_request("PATCH", "v2/community/accounts/{0}/ranks".format(urllib.parse.quote(str(account_id), safe="")), body=dict(data))

    def editProfileFieldsV2(self, account_id, data):
        return self._execute_cms_v2_request("PATCH", "v2/community/accounts/{0}/profile-fields".format(urllib.parse.quote(str(account_id), safe="")), body=dict(data))

    def clockAccountV2(self, account_id, data):
        return self._execute_cms_v2_request("POST", "v2/community/accounts/{0}/clock".format(urllib.parse.quote(str(account_id), safe="")), body=dict(data))

    def getCurrentClockInV2(self, account_id):
        return self._execute_cms_v2_request("GET", "v2/community/accounts/{0}/clock/current".format(urllib.parse.quote(str(account_id), safe="")))

    def getLatestActivityV2(self, account_id, query=None):
        return self._execute_cms_v2_request("GET", "v2/community/accounts/{0}/activity/latest".format(urllib.parse.quote(str(account_id), safe="")), query=dict(query or {}))

    def forceSyncV2(self, account_id, data=None):
        return self._execute_cms_v2_request("POST", "v2/community/accounts/{0}/sync".format(urllib.parse.quote(str(account_id), safe="")), body=dict(data or {}))

    def getServersV2(self):
        return self._execute_cms_v2_request("GET", "v2/community/servers")

    def setServersV2(self, data):
        return self._execute_cms_v2_request("PUT", "v2/community/servers", body=dict(data))

    def addServersV2(self, data):
        return self._execute_cms_v2_request("POST", "v2/community/servers", body=dict(data))

    def getAceConfigV2(self, server_id):
        resolved_server_id = self._resolve_cms_server_id(server_id)
        return self._execute_cms_v2_request("GET", "v2/community/servers/{0}/ace-config".format(resolved_server_id))

    def setAceConfigV2(self, server_id, data):
        resolved_server_id = self._resolve_cms_server_id(server_id)
        return self._execute_cms_v2_request("PATCH", "v2/community/servers/{0}/ace-config".format(resolved_server_id), body=dict(data))

    def setServerTypeV2(self, server_id, data):
        resolved_server_id = self._resolve_cms_server_id(server_id)
        return self._execute_cms_v2_request("PATCH", "v2/community/servers/{0}/type".format(resolved_server_id), body=dict(data))

    def verifyWhitelistV2(self, server_id, data):
        resolved_server_id = self._resolve_cms_server_id(server_id)
        return self._execute_cms_v2_request("POST", "v2/community/servers/{0}/whitelist/check".format(resolved_server_id), body=dict(data))

    def getWhitelistV2(self, server_id):
        resolved_server_id = self._resolve_cms_server_id(server_id)
        return self._execute_cms_v2_request("GET", "v2/community/servers/{0}/whitelist".format(resolved_server_id))

    def createActivityV2(self, server_id, data=None):
        resolved_server_id = self._resolve_cms_server_id(server_id)
        return self._execute_cms_v2_request("POST", "v2/community/servers/{0}/activity".format(resolved_server_id), body=dict(data or {}))

    def startActivityV2(self, server_id, data=None):
        resolved_server_id = self._resolve_cms_server_id(server_id)
        return self._execute_cms_v2_request("POST", "v2/community/servers/{0}/activity/start".format(resolved_server_id), body=dict(data or {}))

    def rsvpEventV2(self, event_id, data):
        return self._execute_cms_v2_request("POST", "v2/community/events/{0}/rsvps".format(urllib.parse.quote(str(event_id), safe="")), body=dict(data))

    def changeFormStageV2(self, form_id, data):
        return self._execute_cms_v2_request("PATCH", "v2/community/forms/{0}/stage".format(urllib.parse.quote(str(form_id), safe="")), body=dict(data))

    def getFormSubmissionsV2(self, template_id, query=None):
        return self._execute_cms_v2_request("GET", "v2/community/forms/{0}/submissions".format(urllib.parse.quote(str(template_id), safe="")), query=dict(query or {}))

    def getFormLockV2(self, template_id):
        return self._execute_cms_v2_request("GET", "v2/community/forms/{0}/lock".format(urllib.parse.quote(str(template_id), safe="")))

    def setFormLockV2(self, template_id, data):
        return self._execute_cms_v2_request("PATCH", "v2/community/forms/{0}/lock".format(urllib.parse.quote(str(template_id), safe="")), body=dict(data))

    def getSubmissionV2(self, submission_id):
        return self._execute_cms_v2_request("GET", "v2/community/forms/submissions/{0}".format(urllib.parse.quote(str(submission_id), safe="")))

    def getRosterV2(self, roster_id, query=None):
        return self._execute_cms_v2_request("GET", "v2/community/rosters/{0}".format(urllib.parse.quote(str(roster_id), safe="")), query=dict(query or {}))

    def getDisciplinaryPointsV2(self, account_id):
        return self._execute_cms_v2_request("GET", "v2/community/disciplinary/accounts/{0}/points".format(urllib.parse.quote(str(account_id), safe="")))

    def getDisciplinaryRecordsV2(self, account_id):
        return self._execute_cms_v2_request("GET", "v2/community/disciplinary/accounts/{0}/records".format(urllib.parse.quote(str(account_id), safe="")))

    def addDisciplinaryRecordV2(self, account_id, data):
        return self._execute_cms_v2_request("POST", "v2/community/disciplinary/accounts/{0}/records".format(urllib.parse.quote(str(account_id), safe="")), body=dict(data))

    def setDisciplinaryRecordPointsV2(self, record_id, data):
        return self._execute_cms_v2_request("PATCH", "v2/community/disciplinary/records/{0}/points".format(urllib.parse.quote(str(record_id), safe="")), body=dict(data))

    def setDisciplinaryRecordReasonV2(self, record_id, data):
        return self._execute_cms_v2_request("PATCH", "v2/community/disciplinary/records/{0}/reason".format(urllib.parse.quote(str(record_id), safe="")), body=dict(data))

    def setDisciplinaryRecordStatusV2(self, record_id, data):
        return self._execute_cms_v2_request("PATCH", "v2/community/disciplinary/records/{0}/status".format(urllib.parse.quote(str(record_id), safe="")), body=dict(data))

    def getOnlinePlayersV2(self, query=None):
        return self._execute_cms_v2_request("GET", "v2/community/erlc/players/online", query=dict(query or {}))

    def getPlayerQueueV2(self, query=None):
        return self._execute_cms_v2_request("GET", "v2/community/erlc/players/queue", query=dict(query or {}))

    def addErlcRecordV2(self, data):
        return self._execute_cms_v2_request("POST", "v2/community/erlc/records", body=dict(data))

    def executeErlcCommandV2(self, data):
        return self._execute_cms_v2_request("POST", "v2/community/erlc/commands", body=dict(data))

    def lockTeamV2(self, data):
        return self._execute_cms_v2_request("POST", "v2/community/erlc/teams/lock", body=dict(data))

    def unlockTeamV2(self, data):
        return self._execute_cms_v2_request("POST", "v2/community/erlc/teams/unlock", body=dict(data))

    def getCurrentSessionV2(self, server_id=None):
        resolved_server_id = server_id if server_id is not None else self.instance.cmsDefaultServerId
        self._assert_positive_integer(resolved_server_id, "serverId")
        return self._execute_cms_v2_request("GET", "v2/community/sessions/current", query={"serverId": int(resolved_server_id)})

    def startSessionV2(self, data):
        return self._execute_cms_v2_request("POST", "v2/community/sessions", body=dict(data))

    def stopSessionV2(self, data):
        return self._execute_cms_v2_request("PATCH", "v2/community/sessions", body=dict(data))

    def cancelSessionV2(self, data):
        return self._execute_cms_v2_request("DELETE", "v2/community/sessions", body=dict(data))
