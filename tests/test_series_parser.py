"""Tests for the series page parser."""

from dsdown.scraper.series_parser import SeriesPageParser


class TestSeriesPageParser:
    """Tests for SeriesPageParser."""

    def test_get_series_name(self, load_fixture):
        """Extracts the series name, excluding the <b>Series</b> label."""
        html = load_fixture("series_page.html")
        parser = SeriesPageParser(html)

        assert parser.get_series_name() == "Awesome Manga"

    def test_get_description(self, load_fixture):
        """Extracts the description from .tag-content-summary."""
        html = load_fixture("series_page.html")
        parser = SeriesPageParser(html)
        description = parser.get_description()

        assert description is not None
        assert "adventures and friendship" in description

    def test_get_cover_image_url(self, load_fixture):
        """Extracts the cover image URL and makes it absolute."""
        html = load_fixture("series_page.html")
        parser = SeriesPageParser(html)
        url = parser.get_cover_image_url()

        assert url is not None
        assert url.startswith("https://dynasty-scans.com/")
        assert "tag_contents_covers" in url

    def test_get_cover_image_url_none(self):
        """Returns None when no cover image exists."""
        html = "<html><body><h2 class='tag-title'>Test</h2></body></html>"
        parser = SeriesPageParser(html)

        assert parser.get_cover_image_url() is None

    def test_get_chapters(self, load_fixture):
        """Extracts chapter URLs and titles from the chapter list."""
        html = load_fixture("series_page.html")
        parser = SeriesPageParser(html)
        chapters = parser.get_chapters()

        assert len(chapters) == 6
        urls = [url for url, _ in chapters]
        assert "/chapters/awesome_manga_ch01" in urls
        assert "/chapters/awesome_manga_ch05" in urls
        assert "/chapters/awesome_manga_extra" in urls

    def test_get_chapters_excludes_sidebar(self, load_fixture):
        """Chapters from the sidebar (Recently Added) are not included."""
        html = load_fixture("series_page.html")
        parser = SeriesPageParser(html)
        chapters = parser.get_chapters()

        urls = [url for url, _ in chapters]
        assert "/chapters/unrelated_chapter" not in urls

    def test_get_chapters_no_duplicates(self):
        """Duplicate chapter links are deduplicated."""
        html = """<html><body>
        <dl class="chapter-list">
            <dd><a href="/chapters/ch01">Ch 01</a></dd>
            <dd><a href="/chapters/ch01">Ch 01</a></dd>
            <dd><a href="/chapters/ch02">Ch 02</a></dd>
        </dl>
        </body></html>"""
        parser = SeriesPageParser(html)
        chapters = parser.get_chapters()

        assert len(chapters) == 2

    def test_get_chapter_volumes(self, load_fixture):
        """Maps chapters to their volume numbers."""
        html = load_fixture("series_page.html")
        parser = SeriesPageParser(html)
        volumes = parser.get_chapter_volumes()

        assert volumes.get("/chapters/awesome_manga_ch01") == 1
        assert volumes.get("/chapters/awesome_manga_ch02") == 1
        assert volumes.get("/chapters/awesome_manga_ch03") == 1
        assert volumes.get("/chapters/awesome_manga_ch04") == 2
        assert volumes.get("/chapters/awesome_manga_ch05") == 2

    def test_get_chapter_volumes_unassigned(self, load_fixture):
        """Chapters after the last volume header are assigned to that volume."""
        html = load_fixture("series_page.html")
        parser = SeriesPageParser(html)
        volumes = parser.get_chapter_volumes()

        # The "Extra" chapter follows "Volume 2" dd entries
        assert volumes.get("/chapters/awesome_manga_extra") == 2

    def test_get_tags(self, load_fixture):
        """Extracts tags from the .tag-tags container."""
        html = load_fixture("series_page.html")
        parser = SeriesPageParser(html)
        tags = parser.get_tags()

        assert "Yuri" in tags
        assert "Romance" in tags
        assert "Comedy" in tags

    def test_get_description_none(self):
        """Returns None when no description exists."""
        html = "<html><body><h2 class='tag-title'>Test</h2></body></html>"
        parser = SeriesPageParser(html)

        assert parser.get_description() is None

    def test_get_series_name_none(self):
        """Returns None when no series name element exists."""
        html = "<html><body><p>No heading</p></body></html>"
        parser = SeriesPageParser(html)

        assert parser.get_series_name() is None

    def test_volume_pattern_variations(self):
        """Recognises different volume header formats."""
        cases = [
            ("Volume 1", 1),
            ("Vol. 1", 1),
            ("Vol 1", 1),
            ("volume 3", 3),
            ("Vol.12", 12),
        ]
        for text, expected in cases:
            html = f"""<html><body>
            <dl class="chapter-list">
                <dt>{text}</dt>
                <dd><a href="/chapters/ch01">Ch 01</a></dd>
            </dl>
            </body></html>"""
            parser = SeriesPageParser(html)
            volumes = parser.get_chapter_volumes()
            assert volumes.get("/chapters/ch01") == expected, f"Failed for: {text}"

    def test_validate_structure_valid(self, load_fixture):
        """Valid page structure returns no warnings."""
        html = load_fixture("series_page.html")
        parser = SeriesPageParser(html)

        assert parser.validate_structure() == []

    def test_validate_structure_missing_elements(self):
        """Missing elements are reported as warnings."""
        html = "<html><body><p>Nothing here</p></body></html>"
        parser = SeriesPageParser(html)
        warnings = parser.validate_structure()

        assert len(warnings) == 2
        assert any("h2" in w for w in warnings)
        assert any("chapters container" in w for w in warnings)
