import argparse
import os
import re
import sys
import warnings
import zipfile
from typing import BinaryIO

import ebooklib
import nltk
from bs4 import BeautifulSoup
from ebooklib import epub
from lxml import etree
from nltk.tokenize import sent_tokenize
from PIL import Image

from .audio_generator import (
    add_cover,
    generate_metadata,
    make_m4b,
    read_book,
)
from .chapter_detector import ChapterDetector, DetectionMethod, HierarchyStyle
from .logger import get_logger, setup_logging
from .mobi_parser import (
    MobiParseError,
    MobiParser,
    is_kindle_file,
)

# Module logger
logger = get_logger(__name__)


namespaces = {
    "calibre": "http://calibre.kovidgoyal.net/2009/metadata",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "opf": "http://www.idpf.org/2007/opf",
    "u": "urn:oasis:names:tc:opendocument:xmlns:container",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

warnings.filterwarnings("ignore", module="ebooklib.epub")


def ensure_punkt() -> None:
    """Ensure NLTK punkt tokenizer is available."""
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt")
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab")


def chap2text_epub(chap: bytes) -> tuple[str | None, list[str]]:
    """Convert EPUB chapter HTML to text.

    Args:
        chap: Raw HTML content of the chapter

    Returns:
        Tuple of (chapter_title, list of paragraphs)
    """
    paragraphs = []
    soup = BeautifulSoup(chap, "html.parser")

    # Extract chapter title (assuming it's in an <h1> tag)
    chapter_title = soup.find("h1")
    if chapter_title:
        chapter_title_text = chapter_title.text.strip()
    else:
        chapter_title_text = None

    # Always skip reading links that are just a number (footnotes)
    for a in soup.findAll("a", href=True):
        if not any(char.isalpha() for char in a.text):
            a.extract()

    chapter_paragraphs = soup.find_all("p")
    if len(chapter_paragraphs) == 0:
        logger.warning(
            "Could not find any paragraph tags <p> in '%s'. Trying with <div>.", chapter_title_text
        )
        chapter_paragraphs = soup.find_all("div")

    for p in chapter_paragraphs:
        paragraph_text = "".join(p.strings).strip()
        paragraphs.append(paragraph_text)

    return chapter_title_text, paragraphs


def get_epub_cover(epub_path: str) -> BinaryIO | None:
    """Extract cover image from EPUB file.

    Args:
        epub_path: Path to the EPUB file

    Returns:
        File-like object containing cover image, or None if not found
    """
    try:
        with zipfile.ZipFile(epub_path) as z:
            t = etree.fromstring(z.read("META-INF/container.xml"))
            rootfile_path = t.xpath("/u:container/u:rootfiles/u:rootfile", namespaces=namespaces)[
                0
            ].get("full-path")

            t = etree.fromstring(z.read(rootfile_path))
            cover_meta = t.xpath("//opf:metadata/opf:meta[@name='cover']", namespaces=namespaces)
            if not cover_meta:
                logger.debug("No cover image found in EPUB metadata")
                return None
            cover_id = cover_meta[0].get("content")

            cover_item = t.xpath(
                "//opf:manifest/opf:item[@id='" + cover_id + "']", namespaces=namespaces
            )
            if not cover_item:
                logger.debug("No cover image found in EPUB manifest")
                return None
            cover_href = cover_item[0].get("href")
            cover_path = os.path.join(os.path.dirname(rootfile_path), cover_href)
            if os.name == "nt" and "\\" in cover_path:
                cover_path = cover_path.replace("\\", "/")
            return z.open(cover_path)
    except FileNotFoundError:
        logger.warning("Could not get cover image of %s", epub_path)


def export(
    book: epub.EpubBook,
    sourcefile: str,
    detection_method: str = "combined",
    max_depth: int | None = None,
    hierarchy_style: str = "flat",
) -> str:
    """Export EPUB to text file with enhanced chapter detection.

    Args:
        book: The ebooklib epub object
        sourcefile: Path to the source EPUB file
        detection_method: Chapter detection method ('toc', 'headings', 'combined', 'auto')
        max_depth: Maximum chapter depth to include (None for all)
        hierarchy_style: How to format chapter titles ('flat', 'numbered', 'indented', 'arrow', 'breadcrumb')
    """
    # Extract cover image
    cover_image = get_epub_cover(sourcefile)
    image_path = None

    if cover_image is not None:
        image = Image.open(cover_image)
        image_filename = sourcefile.replace(".epub", ".png")
        image_path = os.path.join(image_filename)
        image.save(image_path)
        logger.info("Cover image saved to %s", image_path)

    outfile = sourcefile.replace(".epub", ".txt")
    check_for_file(outfile)
    logger.info("Exporting %s to %s", sourcefile, outfile)

    # Use enhanced chapter detection
    try:
        method_enum = DetectionMethod(detection_method)
        style_enum = HierarchyStyle(hierarchy_style)
    except ValueError:
        logger.warning("Invalid detection method or style, using defaults")
        method_enum = DetectionMethod.COMBINED
        style_enum = HierarchyStyle.FLAT

    detector = ChapterDetector(
        sourcefile, method=method_enum, max_depth=max_depth, hierarchy_style=style_enum
    )

    # Detect and export
    detector.detect()

    # Print detected structure for user review
    logger.info("Detected chapter structure:")
    detector.print_structure()

    # Export to text file
    detector.export_to_text(outfile, include_metadata=True, level_markers=True)

    logger.info("Exported to %s", outfile)
    return outfile


def export_legacy(book: epub.EpubBook, sourcefile: str) -> str:
    """Legacy export function (original implementation).

    Kept for backward compatibility.

    Args:
        book: The ebooklib epub object
        sourcefile: Path to the source EPUB file

    Returns:
        Path to the exported text file
    """
    book_contents = []
    cover_image = get_epub_cover(sourcefile)
    image_path = None

    if cover_image is not None:
        image = Image.open(cover_image)
        image_filename = sourcefile.replace(".epub", ".png")
        image_path = os.path.join(image_filename)
        image.save(image_path)
        logger.info("Cover image saved to %s", image_path)

    spine_ids = []
    for spine_tuple in book.spine:
        if spine_tuple[1] == "yes":  # if item in spine is linear
            spine_ids.append(spine_tuple[0])

    items = {}
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            items[item.get_id()] = item

    for id in spine_ids:
        item = items.get(id, None)
        if item is None:
            continue
        chapter_title, chapter_paragraphs = chap2text_epub(item.get_content())
        book_contents.append({"title": chapter_title, "paragraphs": chapter_paragraphs})
    outfile = sourcefile.replace(".epub", ".txt")
    check_for_file(outfile)
    logger.info("Exporting %s to %s", sourcefile, outfile)
    author = book.get_metadata("DC", "creator")[0][0]
    booktitle = book.get_metadata("DC", "title")[0][0]

    with open(outfile, "w", encoding="utf-8") as file:
        file.write(f"Title: {booktitle}\n")
        file.write(f"Author: {author}\n\n")

        file.write("# Title\n")
        file.write(f"{booktitle}, by {author}\n\n")
        for i, chapter in enumerate(book_contents, start=1):
            if chapter["paragraphs"] == [] or chapter["paragraphs"] == [""]:
                continue
            else:
                if chapter["title"] is None:
                    file.write(f"# Part {i}\n")
                else:
                    file.write(f"# {chapter['title']}\n\n")
                for paragraph in chapter["paragraphs"]:
                    clean = re.sub(r"[\s\n]+", " ", paragraph)
                    clean = re.sub(
                        r'[""]', '"', clean
                    )  # Curly double quotes to standard double quotes
                    clean = re.sub(
                        r"[" "]", "'", clean
                    )  # Curly single quotes to standard single quotes
                    file.write(f"{clean}\n\n")


def export_mobi(sourcefile: str) -> str:
    """Export MOBI/AZW file to text file.

    Args:
        sourcefile: Path to the source MOBI/AZW file

    Returns:
        Path to the exported text file
    """
    logger.info("Parsing MOBI/AZW file: %s", sourcefile)

    try:
        parser = MobiParser(sourcefile)
        book = parser.parse()
    except MobiParseError as e:
        logger.error("Error parsing MOBI file: %s", e)
        raise

    # Save cover image if available
    if book.cover_image:
        # Determine output extension
        ext = os.path.splitext(sourcefile)[1].lower()
        image_filename = sourcefile.replace(ext, ".png")
        try:
            with open(image_filename, "wb") as f:
                f.write(book.cover_image)
            logger.info("Cover image saved to %s", image_filename)
        except OSError as e:
            logger.warning("Could not save cover image: %s", e)

    # Determine output filename
    ext = os.path.splitext(sourcefile)[1].lower()
    outfile = sourcefile.replace(ext, ".txt")
    check_for_file(outfile)
    logger.info("Exporting %s to %s", sourcefile, outfile)

    # Write to text file
    with open(outfile, "w", encoding="utf-8") as file:
        file.write(f"Title: {book.title}\n")
        file.write(f"Author: {book.author}\n\n")

        file.write("# Title\n")
        file.write(f"{book.title}, by {book.author}\n\n")

        for i, chapter in enumerate(book.chapters, start=1):
            paragraphs = chapter.get_paragraphs()
            if not paragraphs:
                continue

            if chapter.title:
                file.write(f"# {chapter.title}\n\n")
            else:
                file.write(f"# Part {i}\n\n")

            for paragraph in paragraphs:
                clean = re.sub(r"[\s\n]+", " ", paragraph)
                clean = re.sub(r'[""]', '"', clean)  # Curly double quotes to standard double quotes
                clean = re.sub(
                    r"[" "]", "'", clean
                )  # Curly single quotes to standard single quotes
                file.write(f"{clean}\n\n")

    logger.info("Exported to %s", outfile)
    logger.info("  Title: %s", book.title)
    logger.info("  Author: %s", book.author)
    logger.info("  Chapters: %d", len(book.chapters))

    return outfile


def get_book(
    sourcefile: str, flatten_chapters: bool = True
) -> tuple[list[dict], str, str, list[str]]:
    """Parse a text file into book contents with chapter structure.

    Supports multi-level headers:
    - # Level 1 (Part/Book)
    - ## Level 2 (Chapter)
    - ### Level 3 (Section)
    - etc.

    Args:
        sourcefile: Path to the text file
        flatten_chapters: If True, flatten hierarchy; if False, maintain structure

    Returns:
        Tuple of (book_contents, book_title, book_author, chapter_titles)
    """
    book_contents = []
    book_title = sourcefile
    book_author = "Unknown"
    chapter_titles = []

    with open(sourcefile, encoding="utf-8") as file:
        current_chapter = {"title": "blank", "level": 1, "paragraphs": []}
        initialized_first_chapter = False
        lines_skipped = 0

        for line in file:
            # Handle metadata lines at the start
            if lines_skipped < 2 and (line.startswith("Title") or line.startswith("Author")):
                lines_skipped += 1
                if line.startswith("Title: "):
                    book_title = line.replace("Title: ", "").strip()
                elif line.startswith("Author: "):
                    book_author = line.replace("Author: ", "").strip()
                continue

            line = line.strip()

            # Check for header lines (# ## ### etc.)
            if line.startswith("#"):
                # Count the header level
                header_level = 0
                for char in line:
                    if char == "#":
                        header_level += 1
                    else:
                        break

                # Save previous chapter if it has content
                if current_chapter["paragraphs"] or not initialized_first_chapter:
                    if initialized_first_chapter:
                        book_contents.append(current_chapter)
                    current_chapter = {"title": None, "level": header_level, "paragraphs": []}
                    initialized_first_chapter = True

                # Extract chapter title (strip all leading # and spaces)
                chapter_title = line.lstrip("#").strip()

                if any(c.isalnum() for c in chapter_title):
                    current_chapter["title"] = chapter_title
                    chapter_titles.append(current_chapter["title"])
                else:
                    current_chapter["title"] = "blank"
                    chapter_titles.append("blank")

            elif line:
                if not initialized_first_chapter:
                    chapter_titles.append("blank")
                    initialized_first_chapter = True
                if any(char.isalnum() for char in line):
                    sentences = sent_tokenize(line)
                    cleaned_sentences = [s for s in sentences if any(char.isalnum() for char in s)]
                    line = " ".join(cleaned_sentences)
                    current_chapter["paragraphs"].append(line)

        # Append the last chapter if it contains any paragraphs.
        if current_chapter["paragraphs"]:
            book_contents.append(current_chapter)

    return book_contents, book_title, book_author, chapter_titles


def check_for_file(filename: str) -> None:
    """Check if file exists and prompt for overwrite.

    Args:
        filename: Path to check

    Raises:
        SystemExit: If user declines to overwrite
    """
    if os.path.isfile(filename):
        logger.warning("The file '%s' already exists.", filename)
        overwrite = input("Do you want to overwrite the file? (y/n): ")
        if overwrite.lower() != "y":
            logger.info("Exiting without overwriting the file.")
            sys.exit()
        else:
            os.remove(filename)


def main():
    parser = argparse.ArgumentParser(
        prog="audiobookify",
        description="Convert EPUB or text files to audiobook format with enhanced chapter detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export EPUB with automatic chapter detection
  audiobookify mybook.epub

  # Export with specific detection method
  audiobookify mybook.epub --detect toc

  # Export with numbered chapter hierarchy
  audiobookify mybook.epub --hierarchy numbered

  # Convert text to audiobook
  audiobookify mybook.txt --cover mybook.png

  # Limit chapter depth to 2 levels
  audiobookify mybook.epub --max-depth 2

  # Batch process all EPUBs in a folder
  audiobookify /path/to/books --batch

  # Batch process with recursive folder scan
  audiobookify /path/to/library --batch --recursive

  # Export only (no audio conversion)
  audiobookify /path/to/books --batch --export-only

  # Launch interactive TUI
  audiobookify /path/to/books --tui

  # Preview a voice before converting
  audiobookify --list-voices
  audiobookify --preview-voice --speaker en-US-JennyNeural

  # Adjust speech rate and volume
  audiobookify mybook.txt --rate "+20%" --volume "-10%"

  # Convert only specific chapters
  audiobookify mybook.txt --chapters "1-5"
  audiobookify mybook.txt --chapters "1,3,7,10-"

  # Resume an interrupted conversion
  audiobookify mybook.txt --resume

Note: 'abfy' is available as a short alias for 'audiobookify'

Detection Methods:
  toc       - Use only Table of Contents
  headings  - Use only HTML headings (h1-h6)
  combined  - Combine TOC with headings (default)
  auto      - Automatically choose best method

Hierarchy Styles:
  flat       - No hierarchy indication (default)
  numbered   - 1.1, 1.2, 1.2.1 format
  indented   - Visual indentation
  arrow      - Part 1 > Chapter 1 > Section 1
  breadcrumb - Part 1 / Chapter 1 / Section 1
        """,
    )
    parser.add_argument(
        "sourcefile",
        type=str,
        nargs="?",
        default=None,
        help="EPUB file, text file, or directory to process",
    )
    parser.add_argument(
        "--speaker",
        type=str,
        nargs="?",
        const="en-US-AndrewNeural",
        default="en-US-AndrewNeural",
        help="Speaker voice to use (default: en-US-AndrewNeural). Use 'edge-tts --list-voices' to see options.",
    )
    parser.add_argument(
        "--cover",
        type=str,
        help="JPG/PNG image to use for cover art",
    )
    parser.add_argument(
        "--sentencepause",
        type=int,
        default=1200,
        help="Duration of pause after sentence, in milliseconds (default: 1200)",
    )
    parser.add_argument(
        "--paragraphpause",
        type=int,
        default=1200,
        help="Duration of pause after paragraph, in milliseconds (default: 1200)",
    )

    # Enhanced chapter detection options
    parser.add_argument(
        "--detect",
        type=str,
        choices=["toc", "headings", "combined", "auto"],
        default="combined",
        help="Chapter detection method (default: combined)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum chapter depth to include (default: all levels)",
    )
    parser.add_argument(
        "--hierarchy",
        type=str,
        choices=["flat", "numbered", "indented", "arrow", "breadcrumb"],
        default="flat",
        help="How to display chapter hierarchy in output (default: flat)",
    )
    parser.add_argument(
        "--legacy", action="store_true", help="Use legacy chapter detection (original algorithm)"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview detected chapters without exporting (EPUB only)",
    )

    # Batch processing options
    parser.add_argument(
        "--batch", action="store_true", help="Enable batch processing mode for directories"
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Recursively scan subdirectories for EPUBs (batch mode)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=None,
        help="Output directory for processed files (batch mode)",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Only export EPUBs to text, don't convert to audio (batch mode)",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Process all files, don't skip already processed (batch mode)",
    )
    parser.add_argument(
        "--stop-on-error", action="store_true", help="Stop batch processing if any book fails"
    )
    parser.add_argument("--tui", action="store_true", help="Launch the interactive Terminal UI")

    # Voice preview options
    parser.add_argument(
        "--preview-voice",
        action="store_true",
        help="Generate a voice preview sample for the selected speaker",
    )
    parser.add_argument(
        "--list-voices", action="store_true", help="List available voice options with details"
    )
    parser.add_argument(
        "--rate", type=str, default=None, help="Speech rate adjustment (e.g., '+20%%', '-10%%')"
    )
    parser.add_argument(
        "--volume", type=str, default=None, help="Volume adjustment (e.g., '+50%%', '-25%%')"
    )
    parser.add_argument(
        "--chapters",
        type=str,
        default=None,
        help="Select specific chapters to convert (e.g., '1-5', '1,3,7', '5-')",
    )
    parser.add_argument(
        "--resume", action="store_true", help="Resume from previous incomplete conversion"
    )
    parser.add_argument(
        "--no-resume", action="store_true", help="Start fresh, ignore any saved progress"
    )

    # Audio normalization options
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="Normalize audio for consistent volume across chapters",
    )
    parser.add_argument(
        "--normalize-target",
        type=float,
        default=-16.0,
        help="Target loudness in dBFS for normalization (default: -16.0)",
    )
    parser.add_argument(
        "--normalize-method",
        type=str,
        choices=["peak", "rms"],
        default="peak",
        help="Normalization method: 'peak' or 'rms' (default: peak)",
    )

    # Silence detection options
    parser.add_argument(
        "--trim-silence", action="store_true", help="Trim excessive silence from audio"
    )
    parser.add_argument(
        "--silence-thresh", type=int, default=-40, help="Silence threshold in dBFS (default: -40)"
    )
    parser.add_argument(
        "--max-silence",
        type=int,
        default=2000,
        help="Maximum silence duration in ms before trimming (default: 2000)",
    )

    # Pronunciation dictionary options
    parser.add_argument(
        "--pronunciation",
        type=str,
        default=None,
        help="Path to pronunciation dictionary file (JSON or text format)",
    )
    parser.add_argument(
        "--pronunciation-case-sensitive",
        action="store_true",
        help="Make pronunciation replacements case-sensitive",
    )

    # Multi-voice options
    parser.add_argument(
        "--voice-mapping",
        type=str,
        default=None,
        help="Path to voice mapping file (JSON) for multi-voice support",
    )
    parser.add_argument(
        "--narrator-voice",
        type=str,
        default=None,
        help="Voice to use for narration (non-dialogue text)",
    )

    # Retry configuration
    parser.add_argument(
        "--retry-count",
        type=int,
        default=3,
        help="Number of retry attempts for TTS failures (default: 3)",
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=3,
        help="Delay in seconds between retry attempts (default: 3)",
    )
    parser.add_argument(
        "--max-concurrent", type=int, default=10, help="Maximum concurrent TTS tasks (default: 10)"
    )

    # Logging options
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose (debug) logging"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Quiet mode (only warnings and errors)"
    )

    args = parser.parse_args()

    # Set up logging based on verbosity
    import logging

    if args.verbose:
        setup_logging(level=logging.DEBUG)
    elif args.quiet:
        setup_logging(level=logging.WARNING)
    else:
        setup_logging(level=logging.INFO)

    # Handle voice listing
    if args.list_voices:
        from .voice_preview import AVAILABLE_VOICES

        # Use print for user-facing output that shouldn't go to logs
        print("\nAvailable Voices:")
        print("-" * 60)
        for voice in AVAILABLE_VOICES:
            print(f"  {voice['id']:<25} {voice['description']}")
        print("-" * 60)
        print("\nTip: Use --preview-voice --speaker <voice-id> to hear a sample")
        print("     Or use 'edge-tts --list-voices' for all available voices")
        return

    # Handle voice preview
    if args.preview_voice:
        import shutil
        import subprocess

        from .voice_preview import VoicePreview, VoicePreviewConfig

        config = VoicePreviewConfig(speaker=args.speaker)
        if args.rate:
            config.rate = args.rate
        if args.volume:
            config.volume = args.volume

        preview = VoicePreview(config)
        logger.info("Generating voice preview for: %s", args.speaker)
        if args.rate:
            logger.info("  Rate: %s", args.rate)
        if args.volume:
            logger.info("  Volume: %s", args.volume)

        try:
            output_path = preview.generate_preview_temp()
            logger.info("Preview saved to: %s", output_path)

            # Try to play the audio if a player is available
            players = ["ffplay", "mpv", "vlc", "afplay", "aplay"]
            player_found = False
            for player in players:
                if shutil.which(player):
                    logger.info("Playing with %s...", player)
                    try:
                        if player == "ffplay":
                            subprocess.run(
                                [player, "-nodisp", "-autoexit", output_path],
                                capture_output=True,
                                timeout=30,
                            )
                        else:
                            subprocess.run([player, output_path], capture_output=True, timeout=30)
                        player_found = True
                        break
                    except subprocess.TimeoutExpired:
                        pass
                    except Exception:
                        continue

            if not player_found:
                logger.info(
                    "No audio player found. You can play the file manually: %s", output_path
                )

        except Exception as e:
            logger.error("Error generating preview: %s", e)
            return

        return

    # Launch TUI if requested
    if args.tui:
        from .tui import main as tui_main

        tui_main(args.sourcefile or ".")
        return

    # Validate sourcefile is provided for remaining operations
    if not args.sourcefile:
        parser.error(
            "sourcefile is required (use --list-voices or --preview-voice for voice options without a file)"
        )

    logger.debug("Arguments: %s", args)

    ensure_punkt()

    # Check if batch mode or directory input
    is_directory = os.path.isdir(args.sourcefile)

    if args.batch or is_directory:
        # Batch processing mode
        from .batch_processor import BatchConfig, BatchProcessor

        config = BatchConfig(
            input_path=args.sourcefile,
            output_dir=args.output_dir,
            recursive=args.recursive,
            speaker=args.speaker,
            detection_method=args.detect,
            hierarchy_style=args.hierarchy,
            max_depth=args.max_depth,
            sentence_pause=args.sentencepause,
            paragraph_pause=args.paragraphpause,
            tts_rate=args.rate,
            tts_volume=args.volume,
            chapters=args.chapters,
            skip_existing=not args.no_skip,
            export_only=args.export_only,
            continue_on_error=not args.stop_on_error,
        )

        processor = BatchProcessor(config)
        result = processor.run()

        # Save report
        if result.completed_count > 0 or result.failed_count > 0:
            report_path = result.save_report()
            logger.info("Report saved to: %s", report_path)

        return

    # If we get an epub, export that to txt file, then exit
    if args.sourcefile.endswith(".epub"):
        book = epub.read_epub(args.sourcefile)

        # Preview mode - just show detected structure
        if args.preview:
            logger.info("Previewing chapter detection...")
            try:
                method_enum = DetectionMethod(args.detect)
                style_enum = HierarchyStyle(args.hierarchy)
            except ValueError:
                method_enum = DetectionMethod.COMBINED
                style_enum = HierarchyStyle.FLAT

            detector = ChapterDetector(
                args.sourcefile,
                method=method_enum,
                max_depth=args.max_depth,
                hierarchy_style=style_enum,
            )
            detector.detect()
            logger.info("Detected chapter structure:")
            detector.print_structure()

            # Show summary
            chapters = detector.get_flat_chapters()
            total_paragraphs = sum(len(c["paragraphs"]) for c in chapters)
            logger.info("Summary: %d chapters, %d paragraphs", len(chapters), total_paragraphs)
            sys.exit(0)

        # Use legacy or enhanced export
        if args.legacy:
            export_legacy(book, args.sourcefile)
        else:
            export(
                book,
                args.sourcefile,
                detection_method=args.detect,
                max_depth=args.max_depth,
                hierarchy_style=args.hierarchy,
            )
        sys.exit(0)

    # If we get a MOBI/AZW file, export that to txt file, then exit
    if is_kindle_file(args.sourcefile):
        # Preview mode for MOBI/AZW
        if args.preview:
            logger.info("Previewing MOBI/AZW file structure...")
            try:
                parser = MobiParser(args.sourcefile)
                book = parser.parse()
                logger.info("Title: %s", book.title)
                logger.info("Author: %s", book.author)
                logger.info("Detected chapters:")
                for i, chapter in enumerate(book.chapters, start=1):
                    para_count = len(chapter.get_paragraphs())
                    logger.info("  %d. %s (%d paragraphs)", i, chapter.title, para_count)
                total_paragraphs = sum(len(c.get_paragraphs()) for c in book.chapters)
                logger.info(
                    "Summary: %d chapters, %d paragraphs", len(book.chapters), total_paragraphs
                )
            except MobiParseError as e:
                logger.error("Error: %s", e)
            sys.exit(0)

        # Export MOBI/AZW to text
        export_mobi(args.sourcefile)
        sys.exit(0)

    # Process text file to audiobook
    book_contents, book_title, book_author, chapter_titles = get_book(args.sourcefile)

    # Apply chapter selection if specified
    if args.chapters:
        from .chapter_selector import ChapterSelector

        selector = ChapterSelector(args.chapters)
        logger.info(selector.get_summary())

        # Filter book_contents and chapter_titles together
        selected_indices = selector.get_selected_indices(len(book_contents))
        book_contents = [book_contents[i] for i in selected_indices]
        chapter_titles = [chapter_titles[i] for i in selected_indices]

        if not book_contents:
            logger.error("No chapters match the selection")
            return
        logger.info("Processing %d selected chapters", len(book_contents))

    # State management for pause/resume
    from .pause_resume import ConversionState, StateManager

    output_dir = os.path.dirname(os.path.abspath(args.sourcefile)) or "."
    state_manager = StateManager(output_dir)

    # Check for existing state
    if not args.no_resume and state_manager.has_state():
        state = state_manager.load_state()
        if state and state_manager.state_matches(args.sourcefile):
            if state.is_resumable:
                # Check for existing intermediate files
                existing_parts = [
                    f
                    for f in [f"part{i}.flac" for i in range(1, len(book_contents) + 1)]
                    if os.path.isfile(f)
                ]
                if existing_parts:
                    logger.info(
                        "Resuming conversion: %d/%d chapters completed",
                        len(existing_parts),
                        len(book_contents),
                    )
                    if not args.resume:
                        logger.info("  (use --no-resume to start fresh)")

    # Save state before starting
    state = ConversionState(
        source_file=os.path.abspath(args.sourcefile),
        total_chapters=len(book_contents),
        completed_chapters=0,
        speaker=args.speaker,
        rate=args.rate,
        volume=args.volume,
        chapters_selection=args.chapters,
    )
    state_manager.save_state(state)

    # Set up audio normalizer if requested
    normalizer = None
    if args.normalize:
        from .audio_normalization import AudioNormalizer, NormalizationConfig

        normalizer = AudioNormalizer(
            NormalizationConfig(
                target_dbfs=args.normalize_target, method=args.normalize_method, enabled=True
            )
        )
        logger.info(
            "Audio normalization enabled: %s method, target %.1f dBFS",
            args.normalize_method,
            args.normalize_target,
        )

    # Set up silence detector if requested
    silence_detector = None
    if args.trim_silence:
        from .silence_detection import SilenceConfig, SilenceDetector

        silence_detector = SilenceDetector(
            SilenceConfig(
                silence_thresh=args.silence_thresh, max_silence_len=args.max_silence, enabled=True
            )
        )
        logger.info(
            "Silence trimming enabled: threshold %d dBFS, max %dms",
            args.silence_thresh,
            args.max_silence,
        )

    # Set up pronunciation processor if dictionary provided
    pronunciation_processor = None
    if args.pronunciation:
        from .pronunciation import PronunciationConfig, PronunciationProcessor

        pronunciation_processor = PronunciationProcessor(
            PronunciationConfig(case_sensitive=args.pronunciation_case_sensitive)
        )
        try:
            pronunciation_processor.load_dictionary(args.pronunciation)
            logger.info(
                "Pronunciation dictionary loaded: %d entries", pronunciation_processor.entry_count
            )
        except FileNotFoundError:
            logger.warning("Pronunciation dictionary not found: %s", args.pronunciation)
            pronunciation_processor = None
        except Exception as e:
            logger.warning("Error loading pronunciation dictionary: %s", e)
            pronunciation_processor = None

    # Set up multi-voice processor if voice mapping provided
    multi_voice_processor = None
    if args.voice_mapping or args.narrator_voice:
        from .multi_voice import MultiVoiceProcessor, VoiceMapping

        mapping = VoiceMapping(default_voice=args.speaker)
        if args.narrator_voice:
            mapping.narrator_voice = args.narrator_voice
        multi_voice_processor = MultiVoiceProcessor(mapping)

        if args.voice_mapping:
            try:
                multi_voice_processor.load_mapping(args.voice_mapping)
                logger.info(
                    "Multi-voice enabled: %d character voices loaded",
                    multi_voice_processor.character_count,
                )
            except FileNotFoundError:
                logger.warning("Voice mapping file not found: %s", args.voice_mapping)
                multi_voice_processor = None
            except Exception as e:
                logger.warning("Error loading voice mapping: %s", e)
                multi_voice_processor = None
        elif args.narrator_voice:
            logger.info("Multi-voice enabled: narrator voice set to %s", args.narrator_voice)

    try:
        files = read_book(
            book_contents,
            args.speaker,
            args.paragraphpause,
            args.sentencepause,
            rate=args.rate,
            volume=args.volume,
            pronunciation_processor=pronunciation_processor,
            multi_voice_processor=multi_voice_processor,
            retry_count=args.retry_count,
            retry_delay=args.retry_delay,
        )
        generate_metadata(files, book_author, book_title, chapter_titles)
        m4bfilename = make_m4b(
            files,
            args.sourcefile,
            args.speaker,
            normalizer=normalizer,
            silence_detector=silence_detector,
        )

        # Handle cover image
        cover_path = args.cover
        if not cover_path:
            # Try to find cover with same name as source file
            base_name = args.sourcefile.replace(".txt", "")
            for ext in [".png", ".jpg", ".jpeg"]:
                potential_cover = base_name + ext
                if os.path.isfile(potential_cover):
                    cover_path = potential_cover
                    logger.info("Found cover image: %s", cover_path)
                    break

        if cover_path:
            add_cover(cover_path, m4bfilename)

        # Clear state on successful completion
        state_manager.clear_state()

        logger.info("Audiobook created: %s", m4bfilename)

    except KeyboardInterrupt:
        logger.info("Conversion paused. Run with --resume to continue.")
        # State is already saved, intermediate files preserved
        return
    except Exception as e:
        logger.error("Error during conversion: %s", e)
        logger.info("Intermediate files preserved. Run with --resume to continue.")
        raise


if __name__ == "__main__":
    main()
