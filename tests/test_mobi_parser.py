"""Tests for MOBI/AZW file parser."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from epub2tts_edge.mobi_parser import (
    MobiParser,
    MobiBook,
    MobiChapter,
    MobiParseError,
    is_mobi_file,
    is_azw_file,
    is_kindle_file,
)


class TestMobiBook:
    """Tests for MobiBook dataclass."""

    def test_mobi_book_creation(self):
        """Test creating a MobiBook instance."""
        book = MobiBook(
            title="Test Book",
            author="Test Author",
            chapters=[],
        )
        assert book.title == "Test Book"
        assert book.author == "Test Author"
        assert book.chapters == []

    def test_mobi_book_with_chapters(self):
        """Test MobiBook with chapters."""
        chapters = [
            MobiChapter(title="Chapter 1", content="Content 1", index=0),
            MobiChapter(title="Chapter 2", content="Content 2", index=1),
        ]
        book = MobiBook(
            title="Test Book",
            author="Test Author",
            chapters=chapters,
        )
        assert len(book.chapters) == 2
        assert book.chapters[0].title == "Chapter 1"

    def test_mobi_book_optional_fields(self):
        """Test MobiBook optional fields."""
        book = MobiBook(
            title="Test Book",
            author="Test Author",
            chapters=[],
            language="en",
            publisher="Test Publisher",
            cover_image=b"fake_image_data",
        )
        assert book.language == "en"
        assert book.publisher == "Test Publisher"
        assert book.cover_image == b"fake_image_data"


class TestMobiChapter:
    """Tests for MobiChapter dataclass."""

    def test_mobi_chapter_creation(self):
        """Test creating a MobiChapter instance."""
        chapter = MobiChapter(
            title="Test Chapter",
            content="Test content here.",
            index=0,
        )
        assert chapter.title == "Test Chapter"
        assert chapter.content == "Test content here."
        assert chapter.index == 0

    def test_mobi_chapter_with_html(self):
        """Test MobiChapter with HTML content."""
        chapter = MobiChapter(
            title="Chapter 1",
            content="<p>Paragraph one.</p><p>Paragraph two.</p>",
            index=0,
            is_html=True,
        )
        assert chapter.is_html is True

    def test_mobi_chapter_paragraphs_property(self):
        """Test extracting paragraphs from chapter content."""
        chapter = MobiChapter(
            title="Test Chapter",
            content="First paragraph.\n\nSecond paragraph.\n\nThird paragraph.",
            index=0,
        )
        paragraphs = chapter.get_paragraphs()
        assert len(paragraphs) == 3
        assert paragraphs[0] == "First paragraph."
        assert paragraphs[1] == "Second paragraph."


class TestFileTypeDetection:
    """Tests for file type detection functions."""

    def test_is_mobi_file_with_mobi_extension(self):
        """Test detecting .mobi files."""
        assert is_mobi_file("book.mobi") is True
        assert is_mobi_file("Book.MOBI") is True
        assert is_mobi_file("/path/to/book.mobi") is True

    def test_is_mobi_file_with_other_extension(self):
        """Test non-mobi files return False."""
        assert is_mobi_file("book.epub") is False
        assert is_mobi_file("book.pdf") is False
        assert is_mobi_file("book.txt") is False

    def test_is_azw_file_with_azw_extensions(self):
        """Test detecting .azw and .azw3 files."""
        assert is_azw_file("book.azw") is True
        assert is_azw_file("book.azw3") is True
        assert is_azw_file("book.AZW3") is True

    def test_is_azw_file_with_other_extension(self):
        """Test non-azw files return False."""
        assert is_azw_file("book.epub") is False
        assert is_azw_file("book.mobi") is False

    def test_is_kindle_file_combines_mobi_and_azw(self):
        """Test is_kindle_file detects both MOBI and AZW."""
        assert is_kindle_file("book.mobi") is True
        assert is_kindle_file("book.azw") is True
        assert is_kindle_file("book.azw3") is True
        assert is_kindle_file("book.epub") is False


class TestMobiParser:
    """Tests for MobiParser class."""

    def test_parser_initialization(self):
        """Test parser initialization with file path."""
        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            parser = MobiParser("test.mobi")
            assert parser.file_path == "test.mobi"

    def test_parser_file_not_found(self):
        """Test parser raises error for non-existent file."""
        with pytest.raises(FileNotFoundError):
            MobiParser("nonexistent.mobi")

    def test_parser_invalid_extension(self):
        """Test parser raises error for invalid file type."""
        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            with pytest.raises(ValueError, match="Unsupported file format"):
                MobiParser("book.epub")

    @patch('epub2tts_edge.mobi_parser.mobi')
    @patch('epub2tts_edge.mobi_parser.shutil')
    def test_parse_mobi_file(self, mock_shutil, mock_mobi):
        """Test parsing a MOBI file."""
        # Setup mock for mobi.extract
        mock_mobi.extract.return_value = ("/tmp/mobi_extract", "/tmp/mobi_extract/book.html")

        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            parser = MobiParser("test.mobi")

            # Mock internal methods
            with patch.object(parser, '_read_extracted_html', return_value="<html><body><h1>Chapter 1</h1><p>Content</p></body></html>"):
                with patch.object(parser, '_extract_metadata_from_opf', return_value=("Test Book", "Test Author", None, None)):
                    with patch.object(parser, '_extract_cover_from_extracted', return_value=None):
                        book = parser.parse()

        assert book.title == "Test Book"
        assert book.author == "Test Author"
        assert len(book.chapters) >= 1

    @patch('epub2tts_edge.mobi_parser.mobi')
    @patch('epub2tts_edge.mobi_parser.shutil')
    def test_parse_azw3_file(self, mock_shutil, mock_mobi):
        """Test parsing an AZW3 file."""
        mock_mobi.extract.return_value = ("/tmp/mobi_extract", "/tmp/mobi_extract/book.html")

        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            parser = MobiParser("test.azw3")

            with patch.object(parser, '_read_extracted_html', return_value="<html><body><p>Content</p></body></html>"):
                with patch.object(parser, '_extract_metadata_from_opf', return_value=("AZW3 Book", "Author", None, None)):
                    with patch.object(parser, '_extract_cover_from_extracted', return_value=None):
                        book = parser.parse()

        assert book.title == "AZW3 Book"


class TestMobiParserHTMLExtraction:
    """Tests for HTML content extraction from MOBI files."""

    def test_extract_text_from_html(self):
        """Test extracting plain text from HTML content."""
        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            parser = MobiParser.__new__(MobiParser)
            parser.file_path = "test.mobi"

            html = "<html><body><p>Hello world.</p><p>Second paragraph.</p></body></html>"
            text = parser._html_to_text(html)

            assert "Hello world." in text
            assert "Second paragraph." in text

    def test_extract_text_removes_scripts(self):
        """Test that script tags are removed from content."""
        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            parser = MobiParser.__new__(MobiParser)
            parser.file_path = "test.mobi"

            html = "<html><body><script>alert('bad')</script><p>Good content.</p></body></html>"
            text = parser._html_to_text(html)

            assert "alert" not in text
            assert "Good content." in text

    def test_extract_text_removes_styles(self):
        """Test that style tags are removed from content."""
        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            parser = MobiParser.__new__(MobiParser)
            parser.file_path = "test.mobi"

            html = "<html><head><style>body{color:red}</style></head><body><p>Content.</p></body></html>"
            text = parser._html_to_text(html)

            assert "color:red" not in text
            assert "Content." in text


class TestMobiParserChapterDetection:
    """Tests for chapter detection in MOBI files."""

    def test_detect_chapters_from_headings(self):
        """Test detecting chapters from h1/h2 headings."""
        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            parser = MobiParser.__new__(MobiParser)
            parser.file_path = "test.mobi"

            html = """
            <html><body>
            <h1>Chapter 1</h1>
            <p>First chapter content.</p>
            <h1>Chapter 2</h1>
            <p>Second chapter content.</p>
            </body></html>
            """

            chapters = parser._detect_chapters_from_html(html)

            assert len(chapters) >= 2
            assert chapters[0].title == "Chapter 1"
            assert chapters[1].title == "Chapter 2"

    def test_detect_chapters_with_no_headings(self):
        """Test handling content with no chapter headings."""
        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            parser = MobiParser.__new__(MobiParser)
            parser.file_path = "test.mobi"

            html = "<html><body><p>Just some content without chapters.</p></body></html>"

            chapters = parser._detect_chapters_from_html(html)

            # Should return at least one chapter with all content
            assert len(chapters) >= 1


class TestMobiParserMetadata:
    """Tests for metadata extraction from MOBI files."""

    @patch('epub2tts_edge.mobi_parser.mobi')
    def test_extract_title_and_author(self, mock_mobi):
        """Test extracting title and author from MOBI metadata."""
        mock_book = MagicMock()
        mock_book.title = "The Great Book"
        mock_book.author = "Famous Author"

        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            parser = MobiParser.__new__(MobiParser)
            parser.file_path = "test.mobi"
            parser._mobi_book = mock_book

            title, author, lang, pub = parser._extract_metadata()

            assert title == "The Great Book"
            assert author == "Famous Author"

    def test_extract_metadata_with_missing_fields(self):
        """Test handling missing metadata fields gracefully."""
        mock_book = MagicMock()
        mock_book.title = None
        mock_book.author = None

        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            parser = MobiParser.__new__(MobiParser)
            parser.file_path = "test.mobi"
            parser._mobi_book = mock_book

            title, author, lang, pub = parser._extract_metadata()

            # Should use filename as fallback
            assert title == "test"  # from test.mobi
            assert author == "Unknown Author"


class TestMobiParserCoverExtraction:
    """Tests for cover image extraction from MOBI files."""

    @patch('epub2tts_edge.mobi_parser.mobi')
    def test_extract_cover_image(self, mock_mobi):
        """Test extracting cover image from MOBI file."""
        mock_book = MagicMock()
        fake_cover_data = b'\x89PNG\r\n\x1a\n'  # PNG header
        mock_book.get_cover.return_value = fake_cover_data

        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            parser = MobiParser.__new__(MobiParser)
            parser.file_path = "test.mobi"
            parser._mobi_book = mock_book

            cover = parser._extract_cover()

            assert cover == fake_cover_data

    def test_extract_cover_when_none(self):
        """Test handling when no cover image exists."""
        mock_book = MagicMock()
        mock_book.get_cover.return_value = None

        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            parser = MobiParser.__new__(MobiParser)
            parser.file_path = "test.mobi"
            parser._mobi_book = mock_book

            cover = parser._extract_cover()

            assert cover is None


class TestMobiParserToBookContents:
    """Tests for converting MobiBook to audiobookify format."""

    def test_to_book_contents(self):
        """Test converting MobiBook to book_contents format."""
        chapters = [
            MobiChapter("Chapter 1", "Para 1.\n\nPara 2.", 0),
            MobiChapter("Chapter 2", "Para 3.\n\nPara 4.", 1),
        ]
        book = MobiBook(
            title="Test Book",
            author="Test Author",
            chapters=chapters,
        )

        contents = book.to_book_contents()

        assert len(contents) == 2
        assert contents[0]["title"] == "Chapter 1"
        assert contents[0]["paragraphs"] == ["Para 1.", "Para 2."]
        assert contents[1]["title"] == "Chapter 2"

    def test_to_book_contents_filters_empty_paragraphs(self):
        """Test that empty paragraphs are filtered out."""
        chapters = [
            MobiChapter("Chapter 1", "Para 1.\n\n\n\nPara 2.", 0),
        ]
        book = MobiBook(
            title="Test Book",
            author="Test Author",
            chapters=chapters,
        )

        contents = book.to_book_contents()

        # Should only have 2 paragraphs, not empty ones
        assert len(contents[0]["paragraphs"]) == 2


class TestMobiParserErrorHandling:
    """Tests for error handling in MOBI parser."""

    def test_parse_corrupted_file(self):
        """Test handling of corrupted MOBI file."""
        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            with patch('epub2tts_edge.mobi_parser.mobi') as mock_mobi:
                mock_mobi.extract.side_effect = Exception("Corrupted file")

                parser = MobiParser("corrupted.mobi")

                with pytest.raises(MobiParseError, match="Failed to parse"):
                    parser.parse()

    def test_parse_drm_protected_file(self):
        """Test handling of DRM-protected file."""
        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            with patch('epub2tts_edge.mobi_parser.mobi') as mock_mobi:
                mock_mobi.extract.side_effect = Exception("DRM protected")

                parser = MobiParser("drm.mobi")

                with pytest.raises(MobiParseError):
                    parser.parse()


class TestMobiParserIntegration:
    """Integration tests for MobiParser."""

    @patch('epub2tts_edge.mobi_parser.shutil')
    def test_full_parse_workflow(self, mock_shutil):
        """Test complete parsing workflow with mocked MOBI file."""
        with patch('epub2tts_edge.mobi_parser.os.path.exists', return_value=True):
            with patch('epub2tts_edge.mobi_parser.mobi') as mock_mobi:
                # Setup mock for mobi.extract
                mock_mobi.extract.return_value = ("/tmp/mobi_extract", "/tmp/mobi_extract/book.html")

                # Mock HTML content
                html_content = """
                <html><body>
                <h1>Chapter 1: Introduction</h1>
                <p>Welcome to the book.</p>
                <p>This is the introduction.</p>
                <h1>Chapter 2: Main Content</h1>
                <p>The main content starts here.</p>
                </body></html>
                """

                parser = MobiParser("test.mobi")

                # Mock internal methods for clean test
                with patch.object(parser, '_read_extracted_html', return_value=html_content):
                    with patch.object(parser, '_extract_metadata_from_opf',
                                    return_value=("Integration Test Book", "Test Author", None, None)):
                        with patch.object(parser, '_extract_cover_from_extracted', return_value=None):
                            book = parser.parse()

                assert book.title == "Integration Test Book"
                assert book.author == "Test Author"
