# Zhibo Guide Platform

This directory contains the management console and voice server for the Zhibo Guide museum project. It keeps the general device, model, voice and OTA capabilities of the Xiaozhi ESP32 server and adds a museum knowledge-base bridge.

## Components

- `manager-web/`: Vue 3 management console;
- `manager-api/`: Spring Boot API for users, agents, devices and museum retrieval;
- `xiaozhi-server/`: Python WebSocket voice service and plugin runtime.

The management console calls the `museum-rag` service through `manager-api`. The `search_museum_knowledge` plugin passes retrieved evidence to the configured language model before a guide response is generated.

Run the complete local stack from the repository root:

```powershell
.\start_museum_rag.ps1 -OpenBrowser
```

Local credentials, API keys, model files and device configuration are intentionally excluded from Git. See the root [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md) for upstream attribution and licenses.
