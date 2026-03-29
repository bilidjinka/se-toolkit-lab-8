#!/usr/bin/env python3
"""
Entrypoint for nanobot gateway in Docker.
Resolves environment variables into config.json at runtime.
"""

import json
import os
from pathlib import Path


def main():
    config_dir = Path(__file__).parent
    config_path = config_dir / "config.json"
    resolved_path = Path("/tmp/nanobot.config.resolved.json")
    workspace_dir = config_dir / "workspace"

    with open(config_path, "r") as f:
        config = json.load(f)

    # Override provider settings
    if llm_api_key := os.environ.get("LLM_API_KEY"):
        config["providers"]["custom"]["apiKey"] = llm_api_key

    if llm_api_base := os.environ.get("LLM_API_BASE_URL"):
        config["providers"]["custom"]["apiBase"] = llm_api_base

    if llm_model := os.environ.get("LLM_API_MODEL"):
        config["agents"]["defaults"]["model"] = llm_model

    # Override gateway settings
    if gateway_host := os.environ.get("NANOBOT_GATEWAY_CONTAINER_ADDRESS"):
        config["gateway"]["host"] = gateway_host

    if gateway_port := os.environ.get("NANOBOT_GATEWAY_CONTAINER_PORT"):
        config["gateway"]["port"] = int(gateway_port)

    # Override LMS MCP settings
    if lms_backend_url := os.environ.get("NANOBOT_LMS_BACKEND_URL"):
        config["tools"]["mcpServers"]["lms"]["env"]["NANOBOT_LMS_BACKEND_URL"] = lms_backend_url

    if lms_api_key := os.environ.get("NANOBOT_LMS_API_KEY"):
        config["tools"]["mcpServers"]["lms"]["env"]["NANOBOT_LMS_API_KEY"] = lms_api_key

    # Enable webchat channel
    if webchat_host := os.environ.get("NANOBOT_WEBCHAT_CONTAINER_ADDRESS"):
        config.setdefault("channels", {})
        config["channels"].setdefault("webchat", {})
        config["channels"]["webchat"]["enabled"] = True
        config["channels"]["webchat"]["host"] = webchat_host

    if webchat_port := os.environ.get("NANOBOT_WEBCHAT_CONTAINER_PORT"):
        config["channels"].setdefault("webchat", {})
        config["channels"]["webchat"]["port"] = int(webchat_port)

    # Configure mcp_webchat
    if webchat_relay_url := os.environ.get("NANOBOT_WEBSOCKET_RELAY_URL"):
        config["tools"]["mcpServers"]["webchat"] = {
            "command": "python",
            "args": ["-m", "mcp_webchat"],
            "env": {"NANOBOT_WEBSOCKET_RELAY_URL": webchat_relay_url},
        }

    # Configure mcp-obs for observability
    config["tools"]["mcpServers"]["obs"] = {
        "command": "python",
        "args": ["-m", "mcp_obs"],
        "env": {
            "VICTORIALOGS_URL": os.environ.get("VICTORIALOGS_URL", "http://victorialogs:9428"),
            "VICTORIATRACES_URL": os.environ.get("VICTORIATRACES_URL", "http://victoriatraces:10428"),
        },
    }

    with open(resolved_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"Using config: {resolved_path}")

    os.execvp(
        "nanobot",
        ["nanobot", "gateway", "--config", str(resolved_path), "--workspace", str(workspace_dir)],
    )


if __name__ == "__main__":
    main()
