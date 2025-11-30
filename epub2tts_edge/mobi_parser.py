"""MOBI/AZW file parser for audiobookify.

This module provides functionality to parse MOBI and AZW (Kindle) ebook files
and extract their content for text-to-speech conversion.
"""

import os
import re
import shutil
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from bs4 import BeautifulSoup

try:
    import mobi
    MOBI_AVAILABLE = True
except ImportError:
    mobi = None  # Allows tests to mock this attribute
    MOBI_AVAILABLE = False


class MobiParseError(Exception):
    """Exception raised when MOBI parsing fails."""
    pass


@dataclass
class MobiChapter:
    """Represents a chapter in a MOBI/AZW book.

    Attributes:
        title: The chapter title
        content: The chapter content (plain text or HTML)
        index: The chapter index/position
        is_html: Whether the content is HTML (default False)
    """
    title: str
    content: str
    index: int
    is_html: bool = False

    def get_paragraphs(self) -> List[str]:
        """Extract paragraphs from the chapter content.

        Returns:
            List of paragraph strings
        """
        if self.is_html:
            soup = BeautifulSoup(self.content, 'html.parser')
            paragraphs = []
            for p in soup.find_all(['p', 'div']):
                text = p.get_text(strip=True)
                if text:
                    paragraphs.append(text)
            return paragraphs
        else:
            # Split on double newlines for plain text
            paragraphs = re.split(r'\n\s*\n', self.content)
            return [p.strip() for p in paragraphs if p.strip()]


@dataclass
class MobiBook:
    """Represents a parsed MOBI/AZW book.

    Attributes:
        title: Book title
        author: Book author
        chapters: List of MobiChapter objects
        language: Book language code (optional)
        publisher: Publisher name (optional)
        cover_image: Cover image data as bytes (optional)
    """
    title: str
    author: str
    chapters: List[MobiChapter]
    language: Optional[str] = None
    publisher: Optional[str] = None
    cover_image: Optional[bytes] = None

    def to_book_contents(self) -> List[dict]:
        """Convert to audiobookify book_contents format.

        Returns:
            List of chapter dicts with 'title' and 'paragraphs' keys
        """
        contents = []
        for chapter in self.chapters:
            paragraphs = chapter.get_paragraphs()
            # Filter out empty paragraphs
            paragraphs = [p for p in paragraphs if p.strip()]
            contents.append({
                "title": chapter.title,
                "paragraphs": paragraphs,
            })
        return contents


def is_mobi_file(file_path: str) -> bool:
    """Check if a file is a MOBI file.

    Args:
        file_path: Path to the file

    Returns:
        True if the file has a .mobi extension
    """
    return file_path.lower().endswith('.mobi')


def is_azw_file(file_path: str) -> bool:
    """Check if a file is an AZW/AZW3 file.

    Args:
        file_path: Path to the file

    Returns:
        True if the file has a .azw or .azw3 extension
    """
    lower_path = file_path.lower()
    return lower_path.endswith('.azw') or lower_path.endswith('.azw3')


def is_kindle_file(file_path: str) -> bool:
    """Check if a file is any Kindle format (MOBI or AZW).

    Args:
        file_path: Path to the file

    Returns:
        True if the file is a MOBI, AZW, or AZW3 file
    """
    return is_mobi_file(file_path) or is_azw_file(file_path)


class MobiParser:
    """Parser for MOBI and AZW ebook files.

    This parser extracts content, metadata, and chapter structure from
    MOBI and AZW format ebooks.
    """

    SUPPORTED_EXTENSIONS = {'.mobi', '.azw', '.azw3'}

    def __init__(self, file_path: str):
        """Initialize the MOBI parser.

        Args:
            file_path: Path to the MOBI/AZW file

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is not supported
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {ext}. "
                           f"Supported formats: {', '.join(self.SUPPORTED_EXTENSIONS)}")

        self.file_path = file_path
        self._mobi_book = None
        self._raw_html = None

    def parse(self) -> MobiBook:
        """Parse the MOBI/AZW file.

        Returns:
            MobiBook object with parsed content

        Raises:
            MobiParseError: If parsing fails
        """
        if not MOBI_AVAILABLE:
            raise MobiParseError(
                "The 'mobi' library is not installed. "
                "Install it with: pip install mobi"
            )

        try:
            # Read the MOBI file
            tempdir, extracted_path = mobi.extract(self.file_path)

            # Find the HTML file in extracted content
            html_content = self._read_extracted_html(tempdir)
            self._raw_html = html_content

            # Extract metadata
            title, author, language, publisher = self._extract_metadata_from_opf(tempdir)

            # If no title found, use filename
            if not title:
                title = os.path.splitext(os.path.basename(self.file_path))[0]
            if not author:
                author = "Unknown Author"

            # Detect chapters
            chapters = self._detect_chapters_from_html(html_content)

            # Extract cover
            cover = self._extract_cover_from_extracted(tempdir)

            # Clean up temp directory
            shutil.rmtree(tempdir, ignore_errors=True)

            return MobiBook(
                title=title,
                author=author,
                chapters=chapters,
                language=language,
                publisher=publisher,
                cover_image=cover,
            )

        except MobiParseError:
            raise
        except Exception as e:
            raise MobiParseError(f"Failed to parse MOBI file: {str(e)}")

    def _read_extracted_html(self, tempdir: str) -> str:
        """Read HTML content from extracted MOBI directory.

        Args:
            tempdir: Path to extracted MOBI content

        Returns:
            HTML content as string
        """
        # Look for HTML files in the extracted directory
        html_files = []
        for root, dirs, files in os.walk(tempdir):
            for f in files:
                if f.endswith(('.html', '.htm', '.xhtml')):
                    html_files.append(os.path.join(root, f))

        if not html_files:
            raise MobiParseError("No HTML content found in MOBI file")

        # Read and concatenate all HTML files
        content_parts = []
        for html_file in sorted(html_files):
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                content_parts.append(f.read())

        return '\n'.join(content_parts)

    def _extract_metadata_from_opf(self, tempdir: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Extract metadata from OPF file in extracted content.

        Args:
            tempdir: Path to extracted MOBI content

        Returns:
            Tuple of (title, author, language, publisher)
        """
        title = None
        author = None
        language = None
        publisher = None

        # Find OPF file
        for root, dirs, files in os.walk(tempdir):
            for f in files:
                if f.endswith('.opf'):
                    opf_path = os.path.join(root, f)
                    with open(opf_path, 'r', encoding='utf-8', errors='ignore') as opf_file:
                        soup = BeautifulSoup(opf_file.read(), 'html.parser')

                        # Extract title
                        title_tag = soup.find('dc:title') or soup.find('title')
                        if title_tag:
                            title = title_tag.get_text(strip=True)

                        # Extract author
                        author_tag = soup.find('dc:creator') or soup.find('creator')
                        if author_tag:
                            author = author_tag.get_text(strip=True)

                        # Extract language
                        lang_tag = soup.find('dc:language') or soup.find('language')
                        if lang_tag:
                            language = lang_tag.get_text(strip=True)

                        # Extract publisher
                        pub_tag = soup.find('dc:publisher') or soup.find('publisher')
                        if pub_tag:
                            publisher = pub_tag.get_text(strip=True)

                    break

        return title, author, language, publisher

    def _extract_metadata(self) -> Tuple[str, str, Optional[str], Optional[str]]:
        """Extract metadata from the MOBI book object.

        Returns:
            Tuple of (title, author, language, publisher)
        """
        title = None
        author = None
        language = None
        publisher = None

        if self._mobi_book:
            title = getattr(self._mobi_book, 'title', None)
            author = getattr(self._mobi_book, 'author', None)
            language = getattr(self._mobi_book, 'language', None)
            publisher = getattr(self._mobi_book, 'publisher', None)

        # Fallback to filename if no title
        if not title:
            title = os.path.splitext(os.path.basename(self.file_path))[0]
        if not author:
            author = "Unknown Author"

        return title, author, language, publisher

    def _extract_cover(self) -> Optional[bytes]:
        """Extract cover image from the MOBI file.

        Returns:
            Cover image data as bytes, or None if not found
        """
        if self._mobi_book and hasattr(self._mobi_book, 'get_cover'):
            try:
                return self._mobi_book.get_cover()
            except Exception:
                pass
        return None

    def _extract_cover_from_extracted(self, tempdir: str) -> Optional[bytes]:
        """Extract cover image from extracted MOBI content.

        Args:
            tempdir: Path to extracted MOBI content

        Returns:
            Cover image data as bytes, or None if not found
        """
        # Look for common cover image names
        cover_names = ['cover.jpg', 'cover.jpeg', 'cover.png', 'cover.gif']

        for root, dirs, files in os.walk(tempdir):
            for f in files:
                if f.lower() in cover_names or 'cover' in f.lower():
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        try:
                            with open(os.path.join(root, f), 'rb') as img_file:
                                return img_file.read()
                        except Exception:
                            pass
        return None

    def _read_content(self) -> str:
        """Read the raw content from the MOBI file.

        Returns:
            HTML content as string
        """
        if self._raw_html:
            return self._raw_html
        return ""

    def _html_to_text(self, html: str) -> str:
        """Convert HTML content to plain text.

        Args:
            html: HTML content string

        Returns:
            Plain text extracted from HTML
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style elements
        for element in soup.find_all(['script', 'style', 'head', 'meta', 'link']):
            element.decompose()

        # Get text with paragraph separation
        text_parts = []
        for element in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text = element.get_text(strip=True)
            if text:
                text_parts.append(text)

        return '\n\n'.join(text_parts)

    def _detect_chapters_from_html(self, html: str) -> List[MobiChapter]:
        """Detect chapters from HTML content.

        Args:
            html: HTML content string

        Returns:
            List of MobiChapter objects
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style elements first
        for element in soup.find_all(['script', 'style']):
            element.decompose()

        chapters = []

        # Try to find chapters by headings
        headings = soup.find_all(['h1', 'h2'])

        if headings:
            for i, heading in enumerate(headings):
                title = heading.get_text(strip=True)
                if not title:
                    title = f"Chapter {i + 1}"

                # Get content until next heading
                content_parts = []
                for sibling in heading.find_next_siblings():
                    if sibling.name in ['h1', 'h2']:
                        break
                    text = sibling.get_text(strip=True)
                    if text:
                        content_parts.append(text)

                content = '\n\n'.join(content_parts)

                chapters.append(MobiChapter(
                    title=title,
                    content=content,
                    index=i,
                    is_html=False,
                ))
        else:
            # No headings found - treat entire content as one chapter
            text = self._html_to_text(html)
            chapters.append(MobiChapter(
                title="Content",
                content=text,
                index=0,
                is_html=False,
            ))

        return chapters

    def _extract_chapters(self) -> List[MobiChapter]:
        """Extract chapters from the MOBI content.

        Returns:
            List of MobiChapter objects
        """
        if self._raw_html:
            return self._detect_chapters_from_html(self._raw_html)
        return []
