"""Tests for the releases page parser."""

from datetime import date

from dsdown.scraper.parser import ReleasesParser


class TestReleasesParser:
    """Tests for ReleasesParser."""

    def test_parse_normal_page(self, load_fixture):
        """Parse a typical releases page with multiple dates and chapters."""
        html = load_fixture("releases_page.html")
        parser = ReleasesParser(html)
        chapters = parser.parse()

        assert len(chapters) == 3

    def test_parse_chapter_urls(self, load_fixture):
        """Chapter URLs are extracted correctly."""
        html = load_fixture("releases_page.html")
        chapters = ReleasesParser(html).parse()

        urls = [ch.url for ch in chapters]
        assert "/chapters/awesome_manga_ch10" in urls
        assert "/chapters/cool_series_ch05" in urls
        assert "/chapters/old_chapter_ch01" in urls

    def test_parse_chapter_titles(self, load_fixture):
        """Chapter titles are extracted correctly."""
        html = load_fixture("releases_page.html")
        chapters = ReleasesParser(html).parse()

        assert chapters[0].title == "Awesome Manga ch10"
        assert chapters[1].title == "Cool Series ch05"

    def test_parse_authors(self, load_fixture):
        """Authors are extracted from author links."""
        html = load_fixture("releases_page.html")
        chapters = ReleasesParser(html).parse()

        assert chapters[0].authors == ["Author One"]
        assert chapters[1].authors == ["Author Two", "Author Three"]

    def test_parse_tags_with_bracket_stripping(self, load_fixture):
        """Tags are extracted and brackets are stripped."""
        html = load_fixture("releases_page.html")
        chapters = ReleasesParser(html).parse()

        assert chapters[0].tags == ["Yuri", "Romance"]
        assert chapters[1].tags == ["Action"]

    def test_parse_dates(self, load_fixture):
        """Dates are parsed and assigned to chapters."""
        html = load_fixture("releases_page.html")
        chapters = ReleasesParser(html).parse()

        assert chapters[0].release_date == date(2026, 1, 15)
        assert chapters[1].release_date == date(2026, 1, 15)
        assert chapters[2].release_date == date(2026, 1, 14)

    def test_parse_date_formats(self):
        """All supported date formats are parsed correctly."""
        formats = [
            ("January 15, 2026", date(2026, 1, 15)),
            ("January 15 2026", date(2026, 1, 15)),
            ("Jan 15, 2026", date(2026, 1, 15)),
            ("Jan 15 2026", date(2026, 1, 15)),
        ]
        for date_text, expected in formats:
            html = f"""<html><body><div id="main"><dl>
                <dt>{date_text}</dt>
                <dd><a href="/chapters/test_ch01">Test ch01</a></dd>
            </dl></div></body></html>"""
            chapters = ReleasesParser(html).parse()
            assert len(chapters) == 1, f"Failed for format: {date_text}"
            assert chapters[0].release_date == expected, f"Wrong date for: {date_text}"

    def test_parse_empty_page(self, load_fixture):
        """An empty releases page returns no chapters."""
        html = load_fixture("releases_empty.html")
        chapters = ReleasesParser(html).parse()

        assert chapters == []

    def test_excludes_added_links(self):
        """Links to /chapters/added (pagination) are excluded."""
        html = """<html><body><div id="main"><dl>
            <dt>January 15, 2026</dt>
            <dd><a href="/chapters/added?page=2">Next</a></dd>
            <dd><a href="/chapters/real_chapter">Real Chapter</a></dd>
        </dl></div></body></html>"""
        chapters = ReleasesParser(html).parse()

        assert len(chapters) == 1
        assert chapters[0].url == "/chapters/real_chapter"

    def test_has_next_page_true(self, load_fixture):
        """has_next_page returns True when pagination exists."""
        html = load_fixture("releases_page.html")
        parser = ReleasesParser(html)

        assert parser.has_next_page() is True

    def test_has_next_page_false(self, load_fixture):
        """has_next_page returns False when no pagination."""
        html = load_fixture("releases_empty.html")
        parser = ReleasesParser(html)

        assert parser.has_next_page() is False

    def test_get_next_page_url(self, load_fixture):
        """get_next_page_url returns the correct URL."""
        html = load_fixture("releases_page.html")
        parser = ReleasesParser(html)

        assert parser.get_next_page_url() == "/chapters/added?page=2"

    def test_validate_structure_valid(self, load_fixture):
        """Valid page structure returns no warnings."""
        html = load_fixture("releases_page.html")
        parser = ReleasesParser(html)

        assert parser.validate_structure() == []

    def test_validate_structure_missing_elements(self):
        """Missing elements are reported as warnings."""
        html = "<html><body><p>Nothing here</p></body></html>"
        parser = ReleasesParser(html)
        warnings = parser.validate_structure()

        assert len(warnings) == 3
        assert any("#main" in w for w in warnings)
        assert any("<dt>" in w for w in warnings)
        assert any("<dd>" in w for w in warnings)

    def test_chapter_with_no_tags(self):
        """Chapters without tags get an empty tags list."""
        html = """<html><body><div id="main"><dl>
            <dt>January 15, 2026</dt>
            <dd>
                <a href="/chapters/no_tags_ch01">No Tags ch01</a>
                by <a href="/authors/someone">Someone</a>
            </dd>
        </dl></div></body></html>"""
        chapters = ReleasesParser(html).parse()

        assert len(chapters) == 1
        assert chapters[0].tags == []

    def test_chapter_with_no_authors(self):
        """Chapters without authors get an empty authors list."""
        html = """<html><body><div id="main"><dl>
            <dt>January 15, 2026</dt>
            <dd>
                <a href="/chapters/no_author_ch01">No Author ch01</a>
            </dd>
        </dl></div></body></html>"""
        chapters = ReleasesParser(html).parse()

        assert len(chapters) == 1
        assert chapters[0].authors == []
