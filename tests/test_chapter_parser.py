"""Tests for the chapter page parser."""

from dsdown.scraper.chapter_parser import ChapterPageParser


class TestChapterPageParser:
    """Tests for ChapterPageParser."""

    def test_get_series_url(self, load_fixture):
        """Extracts the series URL from a chapter with a series link."""
        html = load_fixture("chapter_with_series.html")
        parser = ChapterPageParser(html)

        assert parser.get_series_url() == "/series/awesome_manga"

    def test_get_series_name(self, load_fixture):
        """Extracts the series name from the series link text."""
        html = load_fixture("chapter_with_series.html")
        parser = ChapterPageParser(html)

        assert parser.get_series_name() == "Awesome Manga"

    def test_get_series_url_none(self, load_fixture):
        """Returns None when no series link exists."""
        html = load_fixture("chapter_no_series.html")
        parser = ChapterPageParser(html)

        assert parser.get_series_url() is None

    def test_get_series_name_none(self, load_fixture):
        """Returns None when no series link exists."""
        html = load_fixture("chapter_no_series.html")
        parser = ChapterPageParser(html)

        assert parser.get_series_name() is None

    def test_get_title(self, load_fixture):
        """Extracts the title from h2#chapter-title."""
        html = load_fixture("chapter_with_series.html")
        parser = ChapterPageParser(html)

        assert parser.get_title() == "Awesome Manga ch10"

    def test_get_title_fallback(self):
        """Falls back to any h2 when #chapter-title is absent."""
        html = """<html><body>
            <h2>Fallback Title</h2>
        </body></html>"""
        parser = ChapterPageParser(html)

        assert parser.get_title() == "Fallback Title"

    def test_get_tags(self, load_fixture):
        """Extracts tags and deduplicates them."""
        html = load_fixture("chapter_with_series.html")
        parser = ChapterPageParser(html)
        tags = parser.get_tags()

        assert "Yuri" in tags
        assert "Romance" in tags
        # "Romance" appears twice in fixture but should be deduplicated
        assert tags.count("Romance") == 1

    def test_get_authors(self, load_fixture):
        """Extracts authors from author links."""
        html = load_fixture("chapter_with_series.html")
        parser = ChapterPageParser(html)

        assert parser.get_authors() == ["Author One"]

    def test_get_download_url(self):
        """Download URL is constructed from the chapter URL."""
        parser = ChapterPageParser("<html><body></body></html>")

        assert parser.get_download_url("/chapters/test_ch01") == "/chapters/test_ch01/download"

    def test_get_download_url_strips_trailing_slash(self):
        """Trailing slashes are stripped before appending /download."""
        parser = ChapterPageParser("<html><body></body></html>")

        assert parser.get_download_url("/chapters/test_ch01/") == "/chapters/test_ch01/download"

    def test_get_title_none(self):
        """Returns None when no h2 exists."""
        html = "<html><body><p>No title here</p></body></html>"
        parser = ChapterPageParser(html)

        assert parser.get_title() is None

    def test_validate_structure_valid(self, load_fixture):
        """Valid page structure returns no warnings."""
        html = load_fixture("chapter_with_series.html")
        parser = ChapterPageParser(html)

        assert parser.validate_structure() == []

    def test_validate_structure_missing_title(self):
        """Missing title element is reported as a warning."""
        html = "<html><body><p>No heading</p></body></html>"
        parser = ChapterPageParser(html)
        warnings = parser.validate_structure()

        assert len(warnings) == 1
        assert "h2" in warnings[0]
