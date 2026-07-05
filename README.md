# fabric-client

A Python async client library for Microsoft Fabric and Power BI REST APIs.

## Features

- **Full async/await** support via `httpx`
- **MSAL-based authentication** (service principal, user-delegated)
- **Lazy collections** with automatic pagination
- **Automatic token refresh** and caching
- **Typed models** for Fabric and Power BI resources
- **Both Fabric and Power BI APIs** in one client

## Installation

```bash
pip install fabric-client
```

## Quick Start

```python
import asyncio
from fabric_client import FabricClient
from fabric_client.auth.credentials import Credentials

async def main():
    creds = Credentials.service_principal(
        tenant_id="your-tenant-id",
        client_id="your-client-id",
        client_secret="your-client-secret",
    )

    async with FabricClient(creds) as client:
        # List workspaces
        workspaces = await client.workspaces.list()
        async for ws in workspaces:
            print(f"  {ws.name} ({ws.id})")

        # List items in a workspace
        items = await client.items.list(workspace_id="...")
        for item in items:
            print(f"  {item['type']}: {item['displayName']}")

        # Get Power BI datasets
        datasets = await client.datasets.list(group_id="...")
        for ds in datasets:
            print(f"  {ds['name']}")

asyncio.run(main())
```

## Authentication

### Service Principal

```python
creds = Credentials.service_principal(
    tenant_id="...",
    client_id="...",
    client_secret="...",
)
```

### User-delegated

```python
creds = Credentials.user_delegated(
    tenant_id="...",
    client_id="...",
    username="...",
    password="...",
)
```

## API Coverage

### Fabric APIs
- Workspaces (list, get, create, update, delete)
- Items (list, get, create, update, delete)

### Power BI APIs
- Datasets (list, get, refresh, delete)
- Reports (list, get, export)
- Dataflows (list, get, refresh)

More APIs coming soon.

## License

MIT
