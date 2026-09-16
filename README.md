# Sonoran.py

`Sonoran.py` is the Python library for Sonoran CAD and Radio integrations.

This repository currently focuses on the CAD and Radio v2 API surfaces and mirrors the public helper names from `Sonoran.js`.

## Install

```sh
pip install Sonoran.py
```

## Example Usage

```python
from sonoran import Instance, productEnums

instance = Instance(
    apiKey="YOUR_API_KEY",
    communityId="YOUR_COMMUNITY_ID",
    product=productEnums.CAD,
    serverId=1,
)

response = instance.cad.createEmergencyCallV2(
    {
        "serverId": 1,
        "isEmergency": True,
        "caller": "John Doe",
        "location": "101 Alta Street",
        "description": "Structure fire with visible smoke.",
        "deleteAfterMinutes": 30,
    }
)

if response.success:
    print(response.data)
else:
    print(response.reason)
```

```python
penal_codes = instance.cad.getPenalCodesV2()
if penal_codes.success:
    print(penal_codes.data)
```

```python
link_response = instance.cad.setCommunityLinkV2(
    {
        "accountUuid": "USER_ACCOUNT_UUID",
        "secretUuid": "USER_ACCOUNT_SECRET_UUID",
        "communityUserId": "fivem:12345",
    }
)
```

```python
location_response = instance.cad.updateUnitLocationsV2(
    {
        "serverId": 1,
        "updates": [
            {
                "roblox": 123456789,
                "location": "Mission Row",
            }
        ],
    }
)
```

```python
with open("bodycam-clip.webm", "rb") as clip:
    bodycam_response = instance.cad.uploadBodycamRecordingV2(
        {
            "accountUuid": "USER_ACCOUNT_UUID",
            "durationMs": 90000,
            "identId": 123,
            "unitNumber": "1A-12",
            "unitLocation": "Senora Fwy / Route 68",
            "fileName": "bodycam-clip.webm",
            "fileContent": clip.read(),
            "contentType": "video/webm",
        }
    )
```

## Notes

- CAD and Radio v2 helpers are included right now.
- Helper names match `Sonoran.js`.
- Radio v2 clients use `communityId` for `/v2/servers/{communityId}` routes and `roomId` on client creation for room-scoped helpers:

```python
radio = Instance(
    apiKey="YOUR_RADIO_API_KEY",
    communityId="YOUR_COMMUNITY_ID",
    product=productEnums.RADIO,
    roomId=2,
)

radio.setRoomId(1)
```

- `instance.cad.setStationsV2(...)` sends `locations`, `tones`, and `unitColors` at the top level of the request body.
- Bodycam uploads use `instance.cad.uploadBodycamRecordingV2(...)` with multipart form data built by the SDK.
- CAD v2 requests automatically retry `429` responses up to 2 times and respect `Retry-After` when it is provided.
- Account-targeted CAD v2 helpers accept `accountUuid`, `communityUserId`, `roblox`, `discord`, and legacy `apiId` where supported by the backend.
- The import package remains `sonoran`.

## Granular CAD permissions (v2)

Use `getPermissionCatalogV2`, `getAccountPermissionsV2`, and `replaceAccountPermissionsV2` for new permission integrations. The existing `setAccountPermissionsV2` remains a legacy category adapter.

```python
catalog = instance.cad.getPermissionCatalogV2()
account = instance.cad.getAccountPermissionsV2(account_uuid)
response = instance.cad.replaceAccountPermissionsV2(account_uuid, ["global.police"])
# Clear all grants explicitly:
cleared = instance.cad.replaceAccountPermissionsV2(account_uuid, [])
```

Use the account UUID, not a community user ID, in these calls. Fetch the community catalog for exact, case-sensitive grant IDs and template IDs; `legacyGrants` maps uppercase legacy flags to current grants. Replacement overwrites the full grant list (version 2), and an empty list clears it. Never treat a failed read as an empty list. Only pending or active non-owner accounts can be edited. Nonempty grants activate pending accounts subject to the member limit; empty grants make active accounts pending. A granular save ends legacy category inheritance for future record templates.

### Full and selected-field editing

Discover support from `getPermissionCatalogV2()`: use `record.<templateId>.edit.selected` only when that exact grant is returned. It requires the updated CAD backend and may not yet be available during rollout. No SDK method or permission-document version change is required.

- `edit.own`: full editing of records owned by the account.
- `edit.any`: full editing of anyone's records, including the account's own records; field opt-in does not limit this grant on the updated backend.
- `edit.selected`: editing only fields marked **Allow limited editing** (`editableByOthers: true`) on another account's records. It does not include `edit.own` or `edit.any`.
- `supervise`: an additional requirement for supervisor-only fields; it does not grant editing by itself or bypass limited-field opt-in. Read-only fields remain locked for account editing.

Existing grants and field settings are preserved, and the new grant is not automatically assigned. For limited access, remove that template's `edit.any` grant from every source and assign `edit.selected` instead; optionally retain `edit.own`. Permissions from keys or role mappings may combine, and any remaining `edit.any` grants full editing. Fetch the account first and preserve unrelated grants when replacing its complete permission set. Never treat a failed read as an empty grant list. Community API-key record operations retain their existing service authority; these grants govern community accounts.
