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

## Notes

- Only CAD v2 helpers are included right now.
- Helper names match `Sonoran.js`.
- CAD v2 requests automatically retry `429` responses up to 2 times and respect `Retry-After` when it is provided.
- The import package remains `sonoran`.
