# MainV2 Remote Tool Bridge

This is a thin authenticated adapter inside the existing AIVideoEdit Studio stack.

It does **not** introduce a new service, container, execution engine, or production authority.

## Enable

Set both:

```bash
AIVE_REMOTE_ENABLED=1
AIVE_REMOTE_TOKEN=<strong secret>
```

Then run the existing Studio stack normally.

Remote endpoints:

- `GET /api/remote/health`
- `GET /api/remote/capabilities`
- `POST /api/remote/call`

All remote tool calls resolve through the same provider-neutral Tool API already used by Studio/MCP. State-changing production calls therefore remain subject to the boot capsule, session attestation, Runtime Gatekeeper, Jev, and canonical AIVideoEdit guards.

There is no arbitrary shell endpoint.

The included `remote_agent_client.py` is dependency-free and can be used by an authorized sandbox agent against an already-exposed Studio endpoint. Network exposure/TLS remains an operator/deployment concern and is intentionally not re-architected here.
