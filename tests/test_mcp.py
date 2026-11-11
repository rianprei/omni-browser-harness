from io import StringIO
import json
from omni_browser.mcp_server import McpApp, serve, TOOLS

class FakeBrowser:
    def __init__(self): self.closed=False; self.calls=[]
    def open(self, url): self.calls.append(url);return {"url":url}
    def snapshot(self,limit=18000):return {"snapshot":"- heading: test"}
    def close(self): self.closed=True


def test_initialize_and_tools():
    app=McpApp(FakeBrowser())
    v=app.handle({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}})
    assert v["result"]["protocolVersion"]=="2025-06-18"
    tools=app.handle({"jsonrpc":"2.0","id":2,"method":"tools/list"})["result"]["tools"]
    assert len(tools)==13
    assert any(x["name"]=="github_create_repository" for x in tools)
    assert app.handle({"jsonrpc":"2.0","method":"notifications/initialized"}) is None


def test_tool_call_and_missing_args():
    app=McpApp(FakeBrowser())
    response=app.handle({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"browser_open","arguments":{"url":"https://github.com"}}})
    assert not response["result"]["isError"]
    assert json.loads(response["result"]["content"][0]["text"])["url"]=="https://github.com"
    response=app.handle({"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"browser_open","arguments":{}}})
    assert response["result"]["isError"]


def test_github_create_requires_prepare():
    app=McpApp(FakeBrowser())
    response=app.handle({"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"github_create_repository","arguments":{"owner":"rianprei","name":"omni-research-oss","confirm":True}}})
    assert response["result"]["isError"]


def test_stdio_roundtrip():
    commands=[
      {"jsonrpc":"2.0","id":1,"method":"initialize","params":{}},
      {"jsonrpc":"2.0","method":"notifications/initialized"},
      {"jsonrpc":"2.0","id":2,"method":"tools/list"},
      {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"browser_snapshot","arguments":{}}},
    ]
    inp=StringIO("\n".join(map(json.dumps,commands))+"\n")
    out=StringIO()
    b=FakeBrowser()
    serve(stdin=inp,stdout=out,app=McpApp(b))
    responses=[json.loads(s) for s in out.getvalue().splitlines()]
    assert [v["id"] for v in responses]==[1,2,3]
    assert b.closed
    assert "heading" in responses[2]["result"]["content"][0]["text"]
