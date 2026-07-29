"""Integration test — requires a real UMAKU_MCP_TOKEN and network access.

TODO: implement once UmakuMCPClient._do_call_tool is wired. Marked skip
for now so `make test-integration` doesn't fail on the stub.
"""
import pytest

pytestmark = pytest.mark.skip(reason="UmakuMCPClient implementation pending")


async def test_umaku_sprint_status_tool_chain():
    pass
