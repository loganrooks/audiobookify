"""Pytest configuration and shared fixtures for audiobookify tests."""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


# Mark test categories
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files.

    Yields:
        Path to the temporary directory
    """
    temp_path = Path(tempfile.mkdtemp(prefix="audiobookify_test_"))
    yield temp_path
    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to the fixtures directory.

    Returns:
        Path to tests/fixtures directory
    """
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_epub_content() -> dict:
    """Return sample content for creating test EPUBs.

    Returns:
        Dictionary with title, author, and chapters
    """
    return {
        "title": "Test Book",
        "author": "Test Author",
        "chapters": [
            {
                "title": "Chapter 1",
                "content": "<p>This is the first paragraph of chapter one.</p>"
                          "<p>This is the second paragraph with more text.</p>"
            },
            {
                "title": "Chapter 2",
                "content": "<p>Chapter two begins here with interesting content.</p>"
                          "<p>Another paragraph in chapter two.</p>"
                          "<p>A third paragraph to make it more substantial.</p>"
            },
            {
                "title": "Chapter 3",
                "content": "<p>The final chapter has some concluding remarks.</p>"
                          "<p>Thank you for reading this test book.</p>"
            },
        ]
    }


@pytest.fixture
def sample_text_file(temp_dir: Path, sample_epub_content: dict) -> Path:
    """Create a sample text file in the format audiobookify expects.

    Args:
        temp_dir: Temporary directory for the file
        sample_epub_content: Sample content dictionary

    Returns:
        Path to the created text file
    """
    text_file = temp_dir / "test_book.txt"
    with open(text_file, "w", encoding="utf-8") as f:
        f.write(f"Title: {sample_epub_content['title']}\n")
        f.write(f"Author: {sample_epub_content['author']}\n\n")

        for chapter in sample_epub_content["chapters"]:
            f.write(f"# {chapter['title']}\n\n")
            # Extract text from HTML-like content
            content = chapter["content"]
            content = content.replace("<p>", "").replace("</p>", "\n\n")
            f.write(content)

    return text_file


@pytest.fixture
def sample_pronunciation_dict(temp_dir: Path) -> Path:
    """Create a sample pronunciation dictionary.

    Args:
        temp_dir: Temporary directory for the file

    Returns:
        Path to the created dictionary file
    """
    dict_file = temp_dir / "pronunciation.json"
    import json
    with open(dict_file, "w", encoding="utf-8") as f:
        json.dump({
            "Tolkien": "toll-keen",
            "Gandalf": "gan-dalf",
            "CLI": "command line interface"
        }, f)
    return dict_file


@pytest.fixture
def sample_voice_mapping(temp_dir: Path) -> Path:
    """Create a sample voice mapping file.

    Args:
        temp_dir: Temporary directory for the file

    Returns:
        Path to the created mapping file
    """
    mapping_file = temp_dir / "voice_mapping.json"
    import json
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump({
            "default_voice": "en-US-AriaNeural",
            "narrator_voice": "en-US-GuyNeural",
            "character_voices": {
                "Alice": "en-US-JennyNeural",
                "Bob": "en-US-ChristopherNeural"
            }
        }, f)
    return mapping_file


def create_minimal_epub(output_path: Path, content: dict) -> Path:
    """Create a minimal EPUB file for testing.

    This creates a valid EPUB 2.0 file with basic structure.

    Args:
        output_path: Path where the EPUB should be created
        content: Dictionary with title, author, and chapters

    Returns:
        Path to the created EPUB file
    """
    import zipfile

    # Create EPUB structure
    epub_path = output_path / "test_book.epub"

    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub:
        # mimetype (must be first and uncompressed)
        epub.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

        # META-INF/container.xml
        container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
        epub.writestr("META-INF/container.xml", container_xml)

        # OEBPS/content.opf
        manifest_items = ""
        spine_items = ""
        for i, _chapter in enumerate(content["chapters"], start=1):
            manifest_items += f'    <item id="chapter{i}" href="chapter{i}.xhtml" media-type="application/xhtml+xml"/>\n'
            spine_items += f'    <itemref idref="chapter{i}"/>\n'

        content_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{content["title"]}</dc:title>
    <dc:creator>{content["author"]}</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id="bookid">test-book-001</dc:identifier>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
{manifest_items}  </manifest>
  <spine toc="ncx">
{spine_items}  </spine>
</package>'''
        epub.writestr("OEBPS/content.opf", content_opf)

        # OEBPS/toc.ncx
        nav_points = ""
        for i, chapter in enumerate(content["chapters"], start=1):
            nav_points += f'''    <navPoint id="navPoint-{i}" playOrder="{i}">
      <navLabel><text>{chapter["title"]}</text></navLabel>
      <content src="chapter{i}.xhtml"/>
    </navPoint>
'''

        toc_ncx = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="test-book-001"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{content["title"]}</text></docTitle>
  <navMap>
{nav_points}  </navMap>
</ncx>'''
        epub.writestr("OEBPS/toc.ncx", toc_ncx)

        # Chapter files
        for i, chapter in enumerate(content["chapters"], start=1):
            chapter_xhtml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{chapter["title"]}</title>
</head>
<body>
  <h1>{chapter["title"]}</h1>
  {chapter["content"]}
</body>
</html>'''
            epub.writestr(f"OEBPS/chapter{i}.xhtml", chapter_xhtml)

    return epub_path


@pytest.fixture
def sample_epub(temp_dir: Path, sample_epub_content: dict) -> Path:
    """Create a sample EPUB file for testing.

    Args:
        temp_dir: Temporary directory for the file
        sample_epub_content: Sample content dictionary

    Returns:
        Path to the created EPUB file
    """
    return create_minimal_epub(temp_dir, sample_epub_content)
