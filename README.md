# Sonoran.py

`Sonoran.py` is the Python library for Sonoran CAD integrations.

This repository currently focuses on the CAD v2 API surface and mirrors the public helper names from `Sonoran.js`.

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

- Only CAD v2 helpers are included right now.
- Helper names match `Sonoran.js`.
- `instance.cad.setStationsV2(...)` sends `locations`, `tones`, and `unitColors` at the top level of the request body.
- Bodycam uploads use `instance.cad.uploadBodycamRecordingV2(...)` with multipart form data built by the SDK.
- CAD v2 requests automatically retry `429` responses up to 2 times and respect `Retry-After` when it is provided.
- The import package remains `sonoran`.
