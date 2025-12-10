"""EPUB factory for creating test EPUBs with various structures.

This module provides functions to create EPUBs with different content structures
for testing chapter detection, editing, and processing workflows.
"""

import zipfile
from pathlib import Path
from typing import TypedDict


class ChapterContent(TypedDict, total=False):
    """Type definition for chapter content."""

    title: str
    content: str
    level: int  # Heading level (1-6), defaults to 1


class EPUBContent(TypedDict, total=False):
    """Type definition for EPUB content."""

    title: str
    author: str
    chapters: list[ChapterContent]


def create_test_epub(
    output_path: Path,
    title: str = "Test Book",
    author: str = "Test Author",
    chapters: list[tuple[str, str]] | None = None,
) -> Path:
    """Create a minimal EPUB file for testing.

    This creates a valid EPUB 2.0 file with basic structure including
    NCX table of contents for chapter detection testing.

    Args:
        output_path: Directory where the EPUB should be created
        title: Book title
        author: Book author
        chapters: List of (title, content) tuples. If None, uses default content.

    Returns:
        Path to the created EPUB file

    Example:
        >>> epub = create_test_epub(tmp_path, chapters=[
        ...     ("Chapter 1", "First chapter content."),
        ...     ("Chapter 2", "Second chapter content."),
        ... ])
    """
    if chapters is None:
        chapters = [
            ("Chapter 1", "This is the first chapter with some content."),
            ("Chapter 2", "This is the second chapter with more content."),
            ("Chapter 3", "This is the third chapter concluding the book."),
        ]

    # Ensure output_path is a directory
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate safe filename
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
    epub_path = output_path / f"{safe_title}.epub"

    with zipfile.ZipFile(epub_path, "w", zipfile.ZIP_DEFLATED) as epub:
        # mimetype (must be first and uncompressed)
        epub.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

        # META-INF/container.xml
        container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>"""
        epub.writestr("META-INF/container.xml", container_xml)

        # Build manifest and spine
        manifest_items = ""
        spine_items = ""
        for i, _ in enumerate(chapters, start=1):
            manifest_items += f'    <item id="chapter{i}" href="chapter{i}.xhtml" media-type="application/xhtml+xml"/>\n'
            spine_items += f'    <itemref idref="chapter{i}"/>\n'

        # OEBPS/content.opf
        content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id="bookid">test-{safe_title.lower().replace(" ", "-")}</dc:identifier>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
{manifest_items}  </manifest>
  <spine toc="ncx">
{spine_items}  </spine>
</package>"""
        epub.writestr("OEBPS/content.opf", content_opf)

        # OEBPS/toc.ncx
        nav_points = ""
        for i, (ch_title, _) in enumerate(chapters, start=1):
            nav_points += f"""    <navPoint id="navPoint-{i}" playOrder="{i}">
      <navLabel><text>{ch_title}</text></navLabel>
      <content src="chapter{i}.xhtml"/>
    </navPoint>
"""

        toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="test-{safe_title.lower().replace(" ", "-")}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{title}</text></docTitle>
  <navMap>
{nav_points}  </navMap>
</ncx>"""
        epub.writestr("OEBPS/toc.ncx", toc_ncx)

        # Chapter XHTML files
        for i, (ch_title, ch_content) in enumerate(chapters, start=1):
            # Ensure content has paragraph tags
            if not ch_content.strip().startswith("<"):
                ch_content = f"<p>{ch_content}</p>"

            chapter_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{ch_title}</title>
</head>
<body>
  <h1>{ch_title}</h1>
  {ch_content}
</body>
</html>"""
            epub.writestr(f"OEBPS/chapter{i}.xhtml", chapter_xhtml)

    return epub_path


# Predefined fixture configurations for common test scenarios
FIXTURES: dict[str, EPUBContent] = {
    "simple_book": {
        "title": "Simple Test Book",
        "author": "Test Author",
        "chapters": [
            {"title": "Chapter 1", "content": "First chapter content."},
            {"title": "Chapter 2", "content": "Second chapter content."},
        ],
    },
    "book_with_front_matter": {
        "title": "Book With Front Matter",
        "author": "Test Author",
        "chapters": [
            {"title": "Title Page", "content": "Book Title by Author"},
            {"title": "Copyright", "content": "Copyright 2024. All rights reserved."},
            {"title": "Dedication", "content": "For the testers."},
            {"title": "Chapter 1", "content": "The story begins here."},
            {"title": "Chapter 2", "content": "The story continues."},
            {"title": "Chapter 3", "content": "The story ends."},
            {"title": "Notes", "content": "End notes and references."},
            {"title": "Index", "content": "A, B, C..."},
        ],
    },
    "book_with_parts": {
        "title": "Book With Parts",
        "author": "Test Author",
        "chapters": [
            {"title": "Part I: Beginning", "content": ""},
            {"title": "Chapter 1", "content": "First chapter of Part I."},
            {"title": "Chapter 2", "content": "Second chapter of Part I."},
            {"title": "Part II: Middle", "content": ""},
            {"title": "Chapter 3", "content": "First chapter of Part II."},
            {"title": "Chapter 4", "content": "Second chapter of Part II."},
            {"title": "Part III: End", "content": ""},
            {"title": "Chapter 5", "content": "Final chapter."},
        ],
    },
    "empty_chapters": {
        "title": "Book With Empty Chapters",
        "author": "Test Author",
        "chapters": [
            {"title": "Chapter 1", "content": "Real content here."},
            {"title": "Blank Page", "content": ""},
            {"title": "Chapter 2", "content": "More real content."},
            {"title": "Also Empty", "content": "   "},
            {"title": "Chapter 3", "content": "Final content."},
        ],
    },
    "long_chapter_titles": {
        "title": "Book With Long Titles",
        "author": "Test Author",
        "chapters": [
            {
                "title": "Chapter 1: In Which Our Hero Embarks Upon a Great Adventure",
                "content": "The adventure begins.",
            },
            {
                "title": "Chapter 2: Wherein Various Trials and Tribulations Are Encountered",
                "content": "Trials are faced.",
            },
            {
                "title": "Chapter 3: The Conclusion of Our Tale",
                "content": "The end.",
            },
        ],
    },
    "unicode_content": {
        "title": "Book With Unicode",
        "author": "Tëst Àuthör",
        "chapters": [
            {"title": "Chapitre Un", "content": "Contenu français avec accents: é, è, ê."},
            {"title": "章节二", "content": "中文内容测试。"},
            {"title": "Глава Три", "content": "Русский текст для тестирования."},
        ],
    },
    "single_chapter": {
        "title": "Single Chapter Book",
        "author": "Test Author",
        "chapters": [
            {
                "title": "The Only Chapter",
                "content": "This book has only one chapter with substantial content. " * 10,
            },
        ],
    },
    "many_chapters": {
        "title": "Book With Many Chapters",
        "author": "Test Author",
        "chapters": [
            {"title": f"Chapter {i}", "content": f"Content for chapter {i}."} for i in range(1, 26)
        ],
    },
}


def create_fixture_epub(output_path: Path, fixture_name: str) -> Path:
    """Create an EPUB from a predefined fixture.

    Args:
        output_path: Directory where the EPUB should be created
        fixture_name: Name of the fixture from FIXTURES dict

    Returns:
        Path to the created EPUB file

    Raises:
        KeyError: If fixture_name is not in FIXTURES

    Example:
        >>> epub = create_fixture_epub(tmp_path, "book_with_front_matter")
    """
    if fixture_name not in FIXTURES:
        raise KeyError(f"Unknown fixture '{fixture_name}'. Available: {list(FIXTURES.keys())}")

    fixture = FIXTURES[fixture_name]
    chapters = [(ch["title"], ch.get("content", "")) for ch in fixture["chapters"]]

    return create_test_epub(
        output_path,
        title=fixture.get("title", "Test Book"),
        author=fixture.get("author", "Test Author"),
        chapters=chapters,
    )
