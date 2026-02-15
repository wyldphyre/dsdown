"""Live smoke tests that hit the real website.

These tests are skipped by default. Run with: pytest -m live
"""

import pytest

from dsdown.scraper.client import DynastyClient
from dsdown.scraper.parser import ReleasesParser


@pytest.mark.live
@pytest.mark.asyncio
async def test_releases_page_structure():
    """Verify the releases page structure hasn't changed."""
    async with DynastyClient() as client:
        html = await client.get_releases_page()

    parser = ReleasesParser(html)
    warnings = parser.validate_structure()
    assert not warnings, f"Structure warnings: {warnings}"

    chapters = parser.parse()
    assert len(chapters) > 0, "No chapters parsed from live releases page"


@pytest.mark.live
@pytest.mark.asyncio
async def test_releases_page_has_expected_fields():
    """Verify parsed chapters have expected fields populated."""
    async with DynastyClient() as client:
        html = await client.get_releases_page()

    chapters = ReleasesParser(html).parse()
    assert len(chapters) > 0

    first = chapters[0]
    assert first.url.startswith("/chapters/")
    assert len(first.title) > 0
    assert first.release_date is not None
