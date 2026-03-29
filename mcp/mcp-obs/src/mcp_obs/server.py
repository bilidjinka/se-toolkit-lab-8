#!/usr/bin/env python3
"""
MCP server for observability tools (VictoriaLogs and VictoriaTraces).
"""

import asyncio
import os
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("mcp-obs")

# VictoriaLogs URL
VICTORIALOGS_URL = os.environ.get("VICTORIALOGS_URL", "http://localhost:42010")
# VictoriaTraces URL
VICTORIATRACES_URL = os.environ.get("VICTORIATRACES_URL", "http://localhost:42011")


@mcp.tool()
async def logs_search(query: str, limit: int = 50) -> list[dict]:
    """
    Search logs in VictoriaLogs using LogsQL.
    
    Args:
        query: LogsQL query string (e.g., '_time:1h service.name:"Learning Management Service" severity:ERROR')
        limit: Maximum number of log entries to return
    
    Returns:
        List of log entries
    """
    url = f"{VICTORIALOGS_URL}/select/logsql/query"
    params = {"query": query, "limit": limit}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=30.0)
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def logs_error_count(service: str = "Learning Management Service", minutes: int = 60) -> dict:
    """
    Count errors in VictoriaLogs for a specific service over a time window.
    
    Args:
        service: Service name to filter (default: "Learning Management Service")
        minutes: Time window in minutes (default: 60)
    
    Returns:
        Dictionary with error count and details
    """
    query = f'_time:{minutes}m service.name:"{service}" severity:ERROR'
    url = f"{VICTORIALOGS_URL}/select/logsql/query"
    params = {"query": query, "limit": 1000}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=30.0)
        response.raise_for_status()
        data = response.json()
    
    return {
        "service": service,
        "time_window_minutes": minutes,
        "error_count": len(data.get("entries", [])),
        "entries": data.get("entries", [])[:10]  # Return first 10 for context
    }


@mcp.tool()
async def traces_list(service: str = "Learning Management Service", limit: int = 10) -> list[dict]:
    """
    List recent traces for a service from VictoriaTraces.
    
    Args:
        service: Service name to filter
        limit: Maximum number of traces to return
    
    Returns:
        List of trace summaries
    """
    url = f"{VICTORIATRACES_URL}/select/jaeger/api/traces"
    params = {"service": service, "limit": limit}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=30.0)
        response.raise_for_status()
        data = response.json()
    
    # Jaeger API returns {"data": [...]}
    return data.get("data", [])


@mcp.tool()
async def traces_get(trace_id: str) -> dict:
    """
    Get a specific trace by ID from VictoriaTraces.
    
    Args:
        trace_id: The trace ID to fetch
    
    Returns:
        Full trace data with spans
    """
    url = f"{VICTORIATRACES_URL}/select/jaeger/api/traces/{trace_id}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        data = response.json()
    
    # Jaeger API returns {"data": [...]}
    traces = data.get("data", [])
    return traces[0] if traces else {}


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
