"""Minimal interoperable MCP stdio server without additional runtime packages.

MCP clients exchange one JSON-RPC message per line on stdio. The server never
writes logs to stdout. An SDK can replace this adapter without touching browser
or GitHub orchestration logic.
"""
from __future__ import annotations

import json
import sys
from typing import Any

from .core import BrowserHarness
from .github import prepare_repository, submit_repository


PROTOCOL_VERSION = "2025-06-18"


def tool(name, description, properties=None, required=None):
    return {"name": name, "description": description, "inputSchema": {
        "type": "object", "properties": properties or {}, "required": required or [], "additionalProperties": False}}


STR = {"type": "string"}
BOOL = {"type": "boolean"}
INT = {"type": "integer"}

TOOLS = [
    tool("browser_open", "Navigate to an HTTP(S) page; only uses this local browser profile.", {"url": STR}, ["url"]),
    tool("browser_snapshot", "Read accessibility-oriented page structure (no screenshot required).", {"limit": INT}),
    tool("browser_read", "Read visible page text for research.", {"limit": INT}),
    tool("browser_click", "Click Playwright locator; high-impact selectors need confirm=true.", {"selector": STR, "confirm": BOOL}, ["selector"]),
    tool("browser_fill", "Fill a form field via Playwright selector.", {"selector": STR, "value": STR}, ["selector", "value"]),
    tool("browser_press", "Press a key in a focused element.", {"selector": STR, "key": STR}, ["selector", "key"]),
    tool("browser_select", "Select an option in a standard HTML select.", {"selector": STR, "value": STR}, ["selector", "value"]),
    tool("browser_tabs", "List local browser tabs."),
    tool("browser_switch_tab", "Switch active browser tab.", {"index": INT}, ["index"]),
    tool("browser_back", "Navigate one step back."),
    tool("browser_screenshot", "Save screenshot within local browser harness directory. No arbitrary file writes."),
    tool("github_prepare_repository", "Fill new GitHub repo form without creating anything. Must be logged in manually beforehand.", {"owner": STR, "name": STR,"visibility": {"type":"string","enum":["public","private"]},"description":STR}, ["owner", "name"]),
    tool("github_create_repository", "Click Create repository after explicit confirmation, only on prepared GitHub new-repo form.", {"owner":STR, "name":STR,"confirm":BOOL}, ["owner", "name", "confirm"]),
]


class McpApp:
    def __init__(self, browser: BrowserHarness | None = None):
        self.browser = browser or BrowserHarness()
        self.prepared = None

    def invoke(self, name: str, arguments: dict) -> Any:
        if name == "browser_open": return self.browser.open(arguments["url"])
        if name == "browser_snapshot": return self.browser.snapshot(arguments.get("limit", 18_000))
        if name == "browser_read": return self.browser.read(arguments.get("limit", 20_000))
        if name == "browser_click": return self.browser.click(arguments["selector"], arguments.get("confirm", False))
        if name == "browser_fill": return self.browser.fill(arguments["selector"], arguments["value"])
        if name == "browser_press": return self.browser.press(arguments["selector"], arguments["key"])
        if name == "browser_select": return self.browser.select(arguments["selector"], arguments["value"])
        if name == "browser_tabs": return self.browser.tabs()
        if name == "browser_switch_tab": return self.browser.tab_switch(arguments["index"])
        if name == "browser_back": return self.browser.back()
        if name == "browser_screenshot": return self.browser.screenshot()
        if name == "github_prepare_repository":
            self.prepared = None
            result = prepare_repository(self.browser, owner=arguments["owner"],name=arguments["name"],visibility=arguments.get("visibility", "public"),description=arguments.get("description", ""))
            self.prepared = (arguments["owner"], arguments["name"])
            return result
        if name == "github_create_repository":
            if self.prepared != (arguments["owner"], arguments["name"]):
                raise ValueError("Primeiro prepare o mesmo owner/name com github_prepare_repository")
            result = submit_repository(self.browser, owner=arguments["owner"], name=arguments["name"], confirm=arguments["confirm"])
            if result.get("created"):
                self.prepared = None
            return result
        raise ValueError("Ferramenta desconhecida")

    def handle(self, request: dict) -> dict | None:
        if not isinstance(request, dict):
            return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}
        method = request.get("method")
        id_ = request.get("id")
        # Notifications don't carry an id; never reply to them.
        if "id" not in request:
            return None
        try:
            if method == "initialize":
                client_version = (request.get("params") or {}).get("protocolVersion", PROTOCOL_VERSION)
                agreed = client_version if client_version in {"2024-11-05", "2025-03-26", "2025-06-18"} else PROTOCOL_VERSION
                result = {"protocolVersion": agreed, "capabilities": {"tools": {"listChanged": False}},
                          "serverInfo": {"name": "omni-browser-harness", "version": "0.1.0"}}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                params = request.get("params") or {}
                name = params.get("name")
                args = params.get("arguments") or {}
                definition = next((t for t in TOOLS if t["name"] == name), None)
                if not definition:
                    result = {"content": [{"type":"text","text":f"Ferramenta desconhecida: {name}"}], "isError": True}
                elif not isinstance(args, dict) or any(k not in args for k in definition["inputSchema"]["required"]):
                    result = {"content": [{"type":"text","text":"Argumentos obrigatórios ausentes"}], "isError": True}
                else:
                    try:
                        value = self.invoke(name, args)
                        result = {"content": [{"type":"text","text":json.dumps(value, ensure_ascii=False)}],"isError": False}
                    except Exception as exc:
                        result = {"content": [{"type":"text","text":str(exc)[:2000]}], "isError": True}
            elif method in {"resources/list", "prompts/list"}:
                result = {"resources" if method.startswith("resources") else "prompts": []}
            else:
                return {"jsonrpc":"2.0","id":id_,"error":{"code":-32601,"message":"Method not found"}}
            return {"jsonrpc": "2.0", "id": id_, "result": result}
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": id_, "error": {"code": -32603, "message": str(exc)[:1000]}}

    def close(self):
        self.browser.close()


def serve(stdin=None, stdout=None, app=None):
    input_stream = stdin or sys.stdin
    output_stream = stdout or sys.stdout
    app = app or McpApp()
    try:
        for line in input_stream:
            try:
                req = json.loads(line)
                reply = app.handle(req)
            except json.JSONDecodeError:
                reply = {"jsonrpc":"2.0","id":None,"error":{"code":-32700,"message":"Parse error"}}
            if reply is not None:
                output_stream.write(json.dumps(reply,ensure_ascii=False,separators=(",",":")) + "\n")
                output_stream.flush()
    finally:
        app.close()


def main():
    serve()


if __name__ == "__main__":
    main()
