# 🤖 Percival Internet Archive - percival.OS MCP

**Version 0.0.2**

[![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)]()
[![MCP](https://img.shields.io/badge/mcp-server-blue.svg)]()
[![percival.OS](https://img.shields.io/badge/percival.OS-ecosystem-orange.svg)](https://github.com/bill-kopp-ai-dev/percival.OS)

## 📋 Description
**Percival Internet Archive** is a security-focused MCP server for interacting with the Internet Archive. It enables the Nanobot agent to perform governed research and downloads of historical metadata and files.

This server is part of the **percival.OS** ecosystem, a Personal Agentic Operating System designed for autonomy, security, and absolute privacy.

---

## 🛡️ percival.OS Principles
Like all components of `percival.OS`, this MCP server strictly follows our core principles:

- **Privacy & Governance**: Downloads are permitted only to authorized directories within your infrastructure.
- **Data Sovereignty**: The agent accesses historical knowledge without compromising the security of your local host.
- **Hardened Security**: We implement security profiles (`dev`, `staging`, `prod`), destination governance, and prompt-injection mitigation for external content.
- **Transparency**: Based on the original `internetarchive` project, but with stable MCP contracts and strict operational controls.

---

## 🚀 Features & Tools
The server offers the following tools for the agent:

- `archive_search(query, limit=5)`: Search for items in the Internet Archive.
- `archive_get_metadata(identifier)`: Obtain detailed metadata for an item.
- `archive_download_file(identifier, filename, destination_dir, ...)`: Securely download a file to an allowed directory.
- `archive_get_status()`: Check server operational status.
- `archive_reload_config()`: Reload environment configurations.
- `archive_get_security_posture()`: Expose the server's security compliance status.

---

## ⚙️ Configuration in percival.OS (Nanobot)
Add the following configuration to your `~/.nanobot/config.json`:

```json
{
  "tools": {
    "mcpServers": {
      "percival-internetarchive": {
        "command": "/path/to/percival.OS_Dev/.venv/bin/percival-internetarchive-mcp",
        "env": {
          "IA_MCP_SECURITY_PROFILE": "prod",
          "IA_MCP_ALLOWED_DOWNLOAD_DIRS": "/path/to/authorized/downloads",
          "IA_MCP_ROLLOUT_PHASE": "phase1"
        }
      }
    }
  }
}
```

---

## 🛠️ Development & Testing
This server utilizes the shared `percival.OS_Dev` virtual environment.

```bash
# Editable installation in the shared venv
uv pip install -e ./mcp_servers/percival-internetarchive-mcp

# Execution
uv run percival-internetarchive-mcp
```

---

## 📚 About the Project
This server is an integral module of the **percival.OS** project. It provides a secure interface for historical research and data retrieval.

- **Main Repository**: [https://github.com/bill-kopp-ai-dev/percival.OS](https://github.com/bill-kopp-ai-dev/percival.OS)
- **License**: MIT

---
*Developed with ❤️ by the percival.OS Team*
