"""
Enhanced Chapter Detection Module for audiobookify

This module provides intelligent chapter detection from EPUB files by:
1. Parsing the Table of Contents (NCX for EPUB2, NAV for EPUB3)
2. Detecting heading hierarchies (h1-h6) in HTML content
3. Supporting nested chapter structures
4. Providing flexible output formats for audiobook generation
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any
from enum import Enum
from bs4 import BeautifulSoup, Tag
from lxml import etree
import ebooklib
from ebooklib import epub
import zipfile
import os


class DetectionMethod(Enum):
    """Chapter detection method preference."""
    TOC_ONLY = "toc"           # Use only Table of Contents
    HEADINGS_ONLY = "headings"  # Use only HTML headings
    COMBINED = "combined"       # Combine TOC with headings (default)
    AUTO = "auto"              # Automatically choose best method


class HierarchyStyle(Enum):
    """How to display chapter hierarchy in flat output."""
    FLAT = "flat"              # No hierarchy indication
    NUMBERED = "numbered"       # 1.1, 1.2, 1.2.1, etc.
    INDENTED = "indented"       # Indent with spaces/dashes
    ARROW = "arrow"            # Part 1 > Chapter 1 > Section 1
    BREADCRUMB = "breadcrumb"  # Full path: Part 1 / Chapter 1 / Section 1


@dataclass
class ChapterNode:
    """Represents a chapter or section in the book hierarchy."""
    title: str
    level: int = 0  # 0 = root/book, 1 = part, 2 = chapter, 3 = section, etc.
    href: Optional[str] = None  # Reference to content file
    anchor: Optional[str] = None  # Fragment identifier within file
    content: Optional[str] = None  # Extracted text content
    paragraphs: List[str] = field(default_factory=list)
    children: List['ChapterNode'] = field(default_factory=list)
    parent: Optional['ChapterNode'] = None
    play_order: int = 0  # Reading order

    def __post_init__(self):
        # Ensure children have correct parent reference
        for child in self.children:
            child.parent = self

    def add_child(self, child: 'ChapterNode') -> 'ChapterNode':
        """Add a child chapter/section."""
        child.parent = self
        child.level = self.level + 1
        self.children.append(child)
        return child

    def get_path(self) -> List['ChapterNode']:
        """Get the path from root to this node."""
        path = []
        node = self
        while node is not None:
            path.insert(0, node)
            node = node.parent
        return path

    def get_depth(self) -> int:
        """Get the maximum depth of the subtree."""
        if not self.children:
            return 0
        return 1 + max(child.get_depth() for child in self.children)

    def flatten(self, max_depth: Optional[int] = None) -> List['ChapterNode']:
        """Flatten the hierarchy to a list, respecting max_depth."""
        result = []
        if self.level > 0:  # Skip root node
            result.append(self)

        if max_depth is None or self.level < max_depth:
            for child in self.children:
                result.extend(child.flatten(max_depth))

        return result

    def format_title(self, style: HierarchyStyle = HierarchyStyle.FLAT) -> str:
        """Format the title according to hierarchy style."""
        if style == HierarchyStyle.FLAT or self.level <= 1:
            return self.title

        path = self.get_path()

        if style == HierarchyStyle.NUMBERED:
            # Generate numbered format like 1.2.3
            numbers = []
            for i, node in enumerate(path[1:], 1):  # Skip root
                if node.parent:
                    idx = node.parent.children.index(node) + 1
                    numbers.append(str(idx))
            return f"{'.'.join(numbers)} {self.title}"

        elif style == HierarchyStyle.INDENTED:
            indent = "  " * (self.level - 1)
            prefix = "─ " if self.level > 1 else ""
            return f"{indent}{prefix}{self.title}"

        elif style == HierarchyStyle.ARROW:
            titles = [n.title for n in path[1:]]  # Skip root
            return " > ".join(titles)

        elif style == HierarchyStyle.BREADCRUMB:
            titles = [n.title for n in path[1:]]  # Skip root
            return " / ".join(titles)

        return self.title

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "level": self.level,
            "href": self.href,
            "anchor": self.anchor,
            "play_order": self.play_order,
            "children": [child.to_dict() for child in self.children],
            "paragraph_count": len(self.paragraphs)
        }


class TOCParser:
    """Parses Table of Contents from EPUB files (both EPUB2 NCX and EPUB3 NAV)."""

    # XML namespaces for parsing
    NAMESPACES = {
        "ncx": "http://www.daisy.org/z3986/2005/ncx/",
        "epub": "http://www.idpf.org/2007/ops",
        "xhtml": "http://www.w3.org/1999/xhtml",
        "opf": "http://www.idpf.org/2007/opf",
        "dc": "http://purl.org/dc/elements/1.1/",
        "container": "urn:oasis:names:tc:opendocument:xmlns:container",
    }

    def __init__(self, epub_path: str):
        self.epub_path = epub_path
        self.book = epub.read_epub(epub_path)
        self._item_map: Dict[str, Any] = {}
        self._build_item_map()

    def _build_item_map(self):
        """Build a map of href to item for content lookup."""
        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                # Store by various key formats for flexible lookup
                href = item.get_name()
                self._item_map[href] = item
                # Also store by basename
                basename = os.path.basename(href)
                self._item_map[basename] = item

    def parse(self) -> ChapterNode:
        """Parse the TOC and return the chapter hierarchy."""
        root = ChapterNode(title="Root", level=0)

        # Try EPUB3 NAV first (preferred)
        nav_item = self._find_nav_document()
        if nav_item:
            self._parse_nav(nav_item, root)
            if root.children:
                return root

        # Fall back to EPUB2 NCX
        ncx_item = self._find_ncx()
        if ncx_item:
            self._parse_ncx(ncx_item, root)

        return root

    def _find_nav_document(self) -> Optional[Any]:
        """Find the EPUB3 navigation document."""
        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_NAVIGATION:
                return item
        return None

    def _find_ncx(self) -> Optional[Any]:
        """Find the EPUB2 NCX file."""
        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                name = item.get_name().lower()
                if name.endswith('.ncx'):
                    return item

        # Try to find via spine
        try:
            ncx_id = self.book.spine[0] if self.book.spine else None
            if ncx_id:
                return self.book.get_item_with_id(ncx_id)
        except (IndexError, KeyError, AttributeError):
            pass

        return None

    def _parse_nav(self, nav_item: Any, root: ChapterNode):
        """Parse EPUB3 NAV document."""
        content = nav_item.get_content()
        soup = BeautifulSoup(content, 'html.parser')

        # Find the TOC nav element
        nav = soup.find('nav', attrs={'epub:type': 'toc'})
        if not nav:
            nav = soup.find('nav', id='toc')
        if not nav:
            nav = soup.find('nav')

        if nav:
            ol = nav.find('ol')
            if ol:
                self._parse_nav_ol(ol, root, play_order=[0])

    def _parse_nav_ol(self, ol: Tag, parent: ChapterNode, play_order: List[int]):
        """Recursively parse NAV ordered list."""
        for li in ol.find_all('li', recursive=False):
            a = li.find('a')
            if a:
                title = a.get_text(strip=True)
                href = a.get('href', '')

                # Split href into file and anchor
                file_href, anchor = self._split_href(href)

                play_order[0] += 1
                chapter = ChapterNode(
                    title=title,
                    href=file_href,
                    anchor=anchor,
                    play_order=play_order[0]
                )
                parent.add_child(chapter)

                # Check for nested ol
                nested_ol = li.find('ol')
                if nested_ol:
                    self._parse_nav_ol(nested_ol, chapter, play_order)

    def _parse_ncx(self, ncx_item: Any, root: ChapterNode):
        """Parse EPUB2 NCX file."""
        content = ncx_item.get_content()
        try:
            tree = etree.fromstring(content)
        except etree.XMLSyntaxError:
            return

        # Find navMap
        nav_map = tree.find('.//{http://www.daisy.org/z3986/2005/ncx/}navMap')
        if nav_map is None:
            # Try without namespace
            nav_map = tree.find('.//navMap')

        if nav_map is not None:
            self._parse_ncx_navmap(nav_map, root)

    def _parse_ncx_navmap(self, nav_map: Any, parent: ChapterNode):
        """Recursively parse NCX navMap."""
        ns = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}

        nav_points = nav_map.findall('ncx:navPoint', ns)
        if not nav_points:
            nav_points = nav_map.findall('navPoint')

        for nav_point in nav_points:
            # Get title
            nav_label = nav_point.find('ncx:navLabel', ns)
            if nav_label is None:
                nav_label = nav_point.find('navLabel')

            title = ""
            if nav_label is not None:
                text_elem = nav_label.find('ncx:text', ns)
                if text_elem is None:
                    text_elem = nav_label.find('text')
                if text_elem is not None and text_elem.text:
                    title = text_elem.text.strip()

            # Get content href
            content_elem = nav_point.find('ncx:content', ns)
            if content_elem is None:
                content_elem = nav_point.find('content')

            href = ""
            anchor = None
            if content_elem is not None:
                src = content_elem.get('src', '')
                href, anchor = self._split_href(src)

            # Get play order
            play_order = int(nav_point.get('playOrder', 0))

            chapter = ChapterNode(
                title=title,
                href=href,
                anchor=anchor,
                play_order=play_order
            )
            parent.add_child(chapter)

            # Recursively parse nested navPoints
            self._parse_ncx_navmap(nav_point, chapter)

    def _split_href(self, href: str) -> Tuple[str, Optional[str]]:
        """Split href into file path and anchor."""
        if '#' in href:
            parts = href.split('#', 1)
            return parts[0], parts[1]
        return href, None

    def get_item_for_href(self, href: str) -> Optional[Any]:
        """Get the EPUB item for a given href."""
        if not href:
            return None

        # Try direct lookup
        if href in self._item_map:
            return self._item_map[href]

        # Try basename
        basename = os.path.basename(href)
        if basename in self._item_map:
            return self._item_map[basename]

        # Try with different path prefixes
        for key in self._item_map:
            if key.endswith(href) or key.endswith(basename):
                return self._item_map[key]

        return None


class HeadingDetector:
    """Detects and extracts heading hierarchy from HTML content."""

    HEADING_TAGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']

    # Common chapter title patterns
    CHAPTER_PATTERNS = [
        r'^chapter\s+(\d+|[ivxlcdm]+)',  # Chapter 1, Chapter IV
        r'^part\s+(\d+|[ivxlcdm]+)',      # Part 1, Part II
        r'^book\s+(\d+|[ivxlcdm]+)',      # Book 1, Book III
        r'^section\s+(\d+|[ivxlcdm]+)',   # Section 1
        r'^act\s+(\d+|[ivxlcdm]+)',       # Act 1
        r'^scene\s+(\d+|[ivxlcdm]+)',     # Scene 1
        r'^prologue',
        r'^epilogue',
        r'^introduction',
        r'^preface',
        r'^foreword',
        r'^afterword',
        r'^appendix',
        r'^\d+\.',                         # 1. Title
        r'^[ivxlcdm]+\.',                  # IV. Title
    ]

    def __init__(self):
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.CHAPTER_PATTERNS
        ]

    def extract_headings(self, html_content: bytes | str) -> List[Tuple[int, str, Optional[str]]]:
        """
        Extract all headings from HTML content.

        Returns:
            List of tuples: (level, title, element_id)
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        headings = []

        for tag_name in self.HEADING_TAGS:
            for tag in soup.find_all(tag_name):
                level = int(tag_name[1])  # h1 -> 1, h2 -> 2, etc.
                title = tag.get_text(strip=True)
                element_id = tag.get('id')

                if title:  # Only include non-empty headings
                    headings.append((level, title, element_id))

        # Sort by document order (approximate by finding position)
        # This is already in document order from BeautifulSoup
        return headings

    def extract_sections(self, html_content: bytes | str) -> List[Dict[str, Any]]:
        """
        Extract sections with their headings and content.

        Returns:
            List of section dictionaries with heading info and paragraphs
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        sections = []

        # Find all heading elements
        all_headings = soup.find_all(self.HEADING_TAGS)

        for i, heading in enumerate(all_headings):
            level = int(heading.name[1])
            title = heading.get_text(strip=True)
            element_id = heading.get('id')

            if not title:
                continue

            # Collect paragraphs until next heading
            paragraphs = []
            sibling = heading.find_next_sibling()

            while sibling:
                if sibling.name in self.HEADING_TAGS:
                    break
                if sibling.name == 'p':
                    text = sibling.get_text(strip=True)
                    if text:
                        paragraphs.append(text)
                elif sibling.name == 'div':
                    # Check for paragraphs inside div
                    for p in sibling.find_all('p'):
                        text = p.get_text(strip=True)
                        if text:
                            paragraphs.append(text)
                sibling = sibling.find_next_sibling()

            sections.append({
                'level': level,
                'title': title,
                'id': element_id,
                'paragraphs': paragraphs
            })

        return sections

    def is_chapter_title(self, text: str) -> bool:
        """Check if text matches common chapter title patterns."""
        text = text.strip().lower()
        return any(p.match(text) for p in self._compiled_patterns)

    def detect_heading_in_text(self, text: str) -> Optional[int]:
        """
        Detect if plain text looks like a heading and estimate its level.

        Returns:
            Estimated heading level (1-6) or None if not a heading
        """
        text = text.strip()

        # Too long to be a heading
        if len(text) > 100:
            return None

        # Check for chapter patterns (usually level 1 or 2)
        lower_text = text.lower()

        if any(lower_text.startswith(p) for p in ['part ', 'book ']):
            return 1

        if any(lower_text.startswith(p) for p in ['chapter ', 'act ']):
            return 2

        if any(lower_text.startswith(p) for p in ['section ', 'scene ']):
            return 3

        # Numbered patterns
        if re.match(r'^\d+\.?\s+\w', text):
            return 2

        if re.match(r'^[ivxlcdm]+\.?\s+\w', text, re.IGNORECASE):
            return 2

        return None


class ChapterDetector:
    """
    Main class for detecting chapters from EPUB files.
    Combines TOC parsing with heading detection for comprehensive results.
    """

    def __init__(
        self,
        epub_path: str,
        method: DetectionMethod = DetectionMethod.COMBINED,
        max_depth: Optional[int] = None,
        hierarchy_style: HierarchyStyle = HierarchyStyle.FLAT
    ):
        self.epub_path = epub_path
        self.method = method
        self.max_depth = max_depth
        self.hierarchy_style = hierarchy_style

        self.book = epub.read_epub(epub_path)
        self.toc_parser = TOCParser(epub_path)
        self.heading_detector = HeadingDetector()

        self._chapter_tree: Optional[ChapterNode] = None

    def detect(self) -> ChapterNode:
        """
        Detect chapters using the configured method.

        Returns:
            Root ChapterNode containing the chapter hierarchy
        """
        if self.method == DetectionMethod.TOC_ONLY:
            self._chapter_tree = self._detect_from_toc()
        elif self.method == DetectionMethod.HEADINGS_ONLY:
            self._chapter_tree = self._detect_from_headings()
        elif self.method == DetectionMethod.COMBINED:
            self._chapter_tree = self._detect_combined()
        else:  # AUTO
            self._chapter_tree = self._detect_auto()

        # Populate content for all chapters
        self._populate_content(self._chapter_tree)

        return self._chapter_tree

    def _detect_from_toc(self) -> ChapterNode:
        """Detect chapters from Table of Contents only."""
        return self.toc_parser.parse()

    def _detect_from_headings(self) -> ChapterNode:
        """Detect chapters from HTML headings only."""
        root = ChapterNode(title="Root", level=0)

        # Process spine items in order
        spine_ids = [s[0] for s in self.book.spine if s[1] == 'yes']
        items = {item.get_id(): item for item in self.book.get_items()
                 if item.get_type() == ebooklib.ITEM_DOCUMENT}

        play_order = 0
        for spine_id in spine_ids:
            item = items.get(spine_id)
            if not item:
                continue

            content = item.get_content()
            sections = self.heading_detector.extract_sections(content)

            for section in sections:
                play_order += 1
                chapter = ChapterNode(
                    title=section['title'],
                    level=section['level'],
                    href=item.get_name(),
                    anchor=section['id'],
                    paragraphs=section['paragraphs'],
                    play_order=play_order
                )

                # Add to appropriate parent based on level
                self._add_to_hierarchy(root, chapter)

        return root

    def _detect_combined(self) -> ChapterNode:
        """Combine TOC with heading detection for best results."""
        # Start with TOC structure
        toc_tree = self._detect_from_toc()

        # If TOC is empty or shallow, enhance with headings
        if not toc_tree.children or toc_tree.get_depth() < 2:
            headings_tree = self._detect_from_headings()

            if headings_tree.get_depth() > toc_tree.get_depth():
                return headings_tree

            # Merge heading info into TOC
            self._merge_headings_into_toc(toc_tree, headings_tree)

        return toc_tree

    def _detect_auto(self) -> ChapterNode:
        """Automatically choose the best detection method."""
        toc_tree = self._detect_from_toc()
        headings_tree = self._detect_from_headings()

        toc_depth = toc_tree.get_depth()
        toc_count = len(toc_tree.flatten())

        headings_depth = headings_tree.get_depth()
        headings_count = len(headings_tree.flatten())

        # Prefer TOC if it has good structure
        if toc_count > 0 and toc_depth >= 1:
            # If headings provide more detail, merge them
            if headings_depth > toc_depth and headings_count > toc_count:
                return self._detect_combined()
            return toc_tree

        # Fall back to headings
        if headings_count > 0:
            return headings_tree

        # Last resort: create flat structure from spine
        return self._create_flat_structure()

    def _create_flat_structure(self) -> ChapterNode:
        """Create a flat chapter structure from spine items."""
        root = ChapterNode(title="Root", level=0)

        spine_ids = [s[0] for s in self.book.spine if s[1] == 'yes']
        items = {item.get_id(): item for item in self.book.get_items()
                 if item.get_type() == ebooklib.ITEM_DOCUMENT}

        for i, spine_id in enumerate(spine_ids, 1):
            item = items.get(spine_id)
            if not item:
                continue

            # Try to get title from content
            content = item.get_content()
            soup = BeautifulSoup(content, 'html.parser')

            title = None
            for tag in ['h1', 'h2', 'title']:
                elem = soup.find(tag)
                if elem:
                    title = elem.get_text(strip=True)
                    if title:
                        break

            if not title:
                title = f"Part {i}"

            chapter = ChapterNode(
                title=title,
                level=1,
                href=item.get_name(),
                play_order=i
            )
            root.add_child(chapter)

        return root

    def _add_to_hierarchy(self, root: ChapterNode, chapter: ChapterNode):
        """Add a chapter to the hierarchy based on its level."""
        target_level = chapter.level

        # Find the appropriate parent
        parent = root
        while parent.children and parent.children[-1].level < target_level:
            parent = parent.children[-1]

        parent.add_child(chapter)

    def _merge_headings_into_toc(self, toc_tree: ChapterNode, headings_tree: ChapterNode):
        """Merge heading information into TOC structure."""
        # Build href -> headings map
        href_headings: Dict[str, List[ChapterNode]] = {}
        for chapter in headings_tree.flatten():
            href = chapter.href
            if href:
                if href not in href_headings:
                    href_headings[href] = []
                href_headings[href].append(chapter)

        # Enhance TOC chapters with sub-headings
        for toc_chapter in toc_tree.flatten():
            if toc_chapter.href and toc_chapter.href in href_headings:
                headings = href_headings[toc_chapter.href]

                # Add headings that aren't already represented
                for heading in headings:
                    if heading.title != toc_chapter.title:
                        # Check if this is a sub-section
                        if heading.level > 1 and not toc_chapter.children:
                            toc_chapter.add_child(ChapterNode(
                                title=heading.title,
                                level=toc_chapter.level + 1,
                                href=heading.href,
                                anchor=heading.anchor,
                                paragraphs=heading.paragraphs,
                                play_order=heading.play_order
                            ))

    def _populate_content(self, root: ChapterNode):
        """Populate paragraph content for all chapters."""
        # Build href -> content map
        content_map: Dict[str, bytes] = {}
        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                content_map[item.get_name()] = item.get_content()
                # Also map by basename
                content_map[os.path.basename(item.get_name())] = item.get_content()

        for chapter in root.flatten():
            if chapter.paragraphs:  # Already has content
                continue

            href = chapter.href
            if not href:
                continue

            # Find content
            content = content_map.get(href)
            if not content:
                content = content_map.get(os.path.basename(href))

            if not content:
                continue

            # Extract paragraphs
            soup = BeautifulSoup(content, 'html.parser')

            # If there's an anchor, try to find content after it
            start_elem = None
            if chapter.anchor:
                start_elem = soup.find(id=chapter.anchor)

            paragraphs = []

            if start_elem:
                # Get content after the anchor element
                for sibling in start_elem.find_all_next():
                    if sibling.name in HeadingDetector.HEADING_TAGS:
                        # Stop at next heading
                        break
                    if sibling.name == 'p':
                        text = sibling.get_text(strip=True)
                        if text:
                            paragraphs.append(text)
            else:
                # Get all paragraphs from the file
                # Remove link-only text (footnotes)
                for a in soup.find_all('a', href=True):
                    if not any(char.isalpha() for char in a.get_text()):
                        a.extract()

                for p in soup.find_all('p'):
                    text = p.get_text(strip=True)
                    if text:
                        paragraphs.append(text)

                # Fallback to div if no paragraphs
                if not paragraphs:
                    for div in soup.find_all('div'):
                        text = div.get_text(strip=True)
                        if text and len(text) > 20:  # Skip short divs
                            paragraphs.append(text)

            chapter.paragraphs = paragraphs

    def get_flat_chapters(self) -> List[Dict[str, Any]]:
        """
        Get a flat list of chapters suitable for audiobook generation.

        Returns:
            List of chapter dictionaries with title and paragraphs
        """
        if not self._chapter_tree:
            self.detect()

        chapters = []
        for node in self._chapter_tree.flatten(self.max_depth):
            formatted_title = node.format_title(self.hierarchy_style)
            chapters.append({
                'title': formatted_title,
                'original_title': node.title,
                'level': node.level,
                'paragraphs': node.paragraphs,
                'href': node.href,
                'play_order': node.play_order
            })

        return chapters

    def get_chapter_tree(self) -> ChapterNode:
        """Get the full chapter hierarchy tree."""
        if not self._chapter_tree:
            self.detect()
        return self._chapter_tree

    def export_to_text(
        self,
        output_path: str,
        include_metadata: bool = True,
        level_markers: bool = True
    ) -> str:
        """
        Export chapters to text file format compatible with epub2tts.

        Args:
            output_path: Path to output text file
            include_metadata: Include Title/Author header
            level_markers: Use ## for subchapters (multiple # marks)

        Returns:
            Path to the output file
        """
        if not self._chapter_tree:
            self.detect()

        # Get book metadata
        title = "Unknown"
        author = "Unknown"

        try:
            title_meta = self.book.get_metadata('DC', 'title')
            if title_meta:
                title = title_meta[0][0]
        except (IndexError, KeyError, TypeError):
            pass

        try:
            author_meta = self.book.get_metadata('DC', 'creator')
            if author_meta:
                author = author_meta[0][0]
        except (IndexError, KeyError, TypeError):
            pass

        with open(output_path, 'w', encoding='utf-8') as f:
            if include_metadata:
                f.write(f"Title: {title}\n")
                f.write(f"Author: {author}\n\n")

                # Title chapter
                f.write("# Title\n")
                f.write(f"{title}, by {author}\n\n")

            for chapter in self._chapter_tree.flatten(self.max_depth):
                # Determine header level
                if level_markers:
                    markers = '#' * min(chapter.level, 6)
                else:
                    markers = '#'

                title = chapter.format_title(self.hierarchy_style)
                f.write(f"{markers} {title}\n\n")

                for paragraph in chapter.paragraphs:
                    # Clean up text
                    clean = re.sub(r'[\s\n]+', ' ', paragraph)
                    clean = re.sub(r'[\u201c\u201d]', '"', clean)
                    clean = re.sub(r'[\u2018\u2019]', "'", clean)
                    f.write(f"{clean}\n\n")

        return output_path

    def print_structure(self, node: Optional[ChapterNode] = None, indent: int = 0):
        """Print the chapter structure for debugging."""
        if node is None:
            node = self._chapter_tree or self.detect()

        if node.level > 0:
            prefix = "  " * indent + ("├─ " if indent > 0 else "")
            para_count = len(node.paragraphs)
            print(f"{prefix}{node.title} (level {node.level}, {para_count} paragraphs)")

        for child in node.children:
            self.print_structure(child, indent + 1)


def detect_chapters(
    epub_path: str,
    method: str = "combined",
    max_depth: Optional[int] = None,
    hierarchy_style: str = "flat"
) -> List[Dict[str, Any]]:
    """
    Convenience function to detect chapters from an EPUB file.

    Args:
        epub_path: Path to the EPUB file
        method: Detection method ('toc', 'headings', 'combined', 'auto')
        max_depth: Maximum chapter depth to include
        hierarchy_style: How to format titles ('flat', 'numbered', 'indented', 'arrow', 'breadcrumb')

    Returns:
        List of chapter dictionaries
    """
    method_enum = DetectionMethod(method)
    style_enum = HierarchyStyle(hierarchy_style)

    detector = ChapterDetector(
        epub_path,
        method=method_enum,
        max_depth=max_depth,
        hierarchy_style=style_enum
    )

    return detector.get_flat_chapters()
