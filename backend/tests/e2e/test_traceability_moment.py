"""E2E test — requires the full docker-composed stack up (make run) and a
seeded Umaku workspace (see scripts/seed_umaku.md).

TODO: implement once the full stack is wired end to end. Marked skip for
now so `make test-e2e` doesn't fail on the stub.
"""
import pytest

pytestmark = pytest.mark.skip(reason="Full stack wiring pending")


async def test_traceability_moment_produces_four_spans():
    """Should hit POST /scenarios/traceability and assert
    tool_call_count == 4 and all_calls_succeeded is True."""
    pass
