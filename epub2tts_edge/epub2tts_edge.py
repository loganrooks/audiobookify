import argparse
import asyncio
import concurrent.futures
import os
import re
import subprocess
import time
import warnings
import sys
from tqdm import tqdm


from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
import edge_tts
from lxml import etree
from mutagen import mp4
import nltk
from nltk.tokenize import sent_tokenize
from PIL import Image
from pydub import AudioSegment
import zipfile

from .chapter_detector import (
    ChapterDetector,
    DetectionMethod,
    HierarchyStyle,
    detect_chapters
)


namespaces = {
   "calibre":"http://calibre.kovidgoyal.net/2009/metadata",
   "dc":"http://purl.org/dc/elements/1.1/",
   "dcterms":"http://purl.org/dc/terms/",
   "opf":"http://www.idpf.org/2007/opf",
   "u":"urn:oasis:names:tc:opendocument:xmlns:container",
   "xsi":"http://www.w3.org/2001/XMLSchema-instance",
}

warnings.filterwarnings("ignore", module="ebooklib.epub")

def ensure_punkt():
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt")
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab")

def chap2text_epub(chap):
    blacklist = [
        "[document]",
        "noscript",
        "header",
        "html",
        "meta",
        "head",
        "input",
        "script",
    ]
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
        print(f"Could not find any paragraph tags <p> in \"{chapter_title_text}\". Trying with <div>.")
        chapter_paragraphs = soup.find_all("div")

    for p in chapter_paragraphs:
        paragraph_text = "".join(p.strings).strip()
        paragraphs.append(paragraph_text)

    return chapter_title_text, paragraphs

def get_epub_cover(epub_path):
    try:
        with zipfile.ZipFile(epub_path) as z:
            t = etree.fromstring(z.read("META-INF/container.xml"))
            rootfile_path =  t.xpath("/u:container/u:rootfiles/u:rootfile",
                                        namespaces=namespaces)[0].get("full-path")

            t = etree.fromstring(z.read(rootfile_path))
            cover_meta = t.xpath("//opf:metadata/opf:meta[@name='cover']",
                                        namespaces=namespaces)
            if not cover_meta:
                print("No cover image found.")
                return None
            cover_id = cover_meta[0].get("content")

            cover_item = t.xpath("//opf:manifest/opf:item[@id='" + cover_id + "']",
                                            namespaces=namespaces)
            if not cover_item:
                print("No cover image found.")
                return None
            cover_href = cover_item[0].get("href")
            cover_path = os.path.join(os.path.dirname(rootfile_path), cover_href)
            if os.name == 'nt' and '\\' in cover_path:
                cover_path = cover_path.replace("\\", "/")
            return z.open(cover_path)
    except FileNotFoundError:
        print(f"Could not get cover image of {epub_path}")

def export(book, sourcefile, detection_method="combined", max_depth=None, hierarchy_style="flat"):
    """
    Export EPUB to text file with enhanced chapter detection.

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
        print(f"Cover image saved to {image_path}")

    outfile = sourcefile.replace(".epub", ".txt")
    check_for_file(outfile)
    print(f"Exporting {sourcefile} to {outfile}")

    # Use enhanced chapter detection
    try:
        method_enum = DetectionMethod(detection_method)
        style_enum = HierarchyStyle(hierarchy_style)
    except ValueError:
        print(f"Invalid detection method or style, using defaults")
        method_enum = DetectionMethod.COMBINED
        style_enum = HierarchyStyle.FLAT

    detector = ChapterDetector(
        sourcefile,
        method=method_enum,
        max_depth=max_depth,
        hierarchy_style=style_enum
    )

    # Detect and export
    detector.detect()

    # Print detected structure for user review
    print("\nDetected chapter structure:")
    detector.print_structure()
    print()

    # Export to text file
    detector.export_to_text(outfile, include_metadata=True, level_markers=True)

    print(f"\nExported to {outfile}")
    return outfile


def export_legacy(book, sourcefile):
    """
    Legacy export function (original implementation).
    Kept for backward compatibility.
    """
    book_contents = []
    cover_image = get_epub_cover(sourcefile)
    image_path = None

    if cover_image is not None:
        image = Image.open(cover_image)
        image_filename = sourcefile.replace(".epub", ".png")
        image_path = os.path.join(image_filename)
        image.save(image_path)
        print(f"Cover image saved to {image_path}")

    spine_ids = []
    for spine_tuple in book.spine:
        if spine_tuple[1] == 'yes': # if item in spine is linear
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
    print(f"Exporting {sourcefile} to {outfile}")
    author = book.get_metadata("DC", "creator")[0][0]
    booktitle = book.get_metadata("DC", "title")[0][0]

    with open(outfile, "w", encoding='utf-8') as file:
        file.write(f"Title: {booktitle}\n")
        file.write(f"Author: {author}\n\n")

        file.write(f"# Title\n")
        file.write(f"{booktitle}, by {author}\n\n")
        for i, chapter in enumerate(book_contents, start=1):
            if chapter["paragraphs"] == [] or chapter["paragraphs"] == ['']:
                continue
            else:
                if chapter["title"] == None:
                    file.write(f"# Part {i}\n")
                else:
                    file.write(f"# {chapter['title']}\n\n")
                for paragraph in chapter["paragraphs"]:
                    clean = re.sub(r'[\s\n]+', ' ', paragraph)
                    clean = re.sub(r'[""]', '"', clean)  # Curly double quotes to standard double quotes
                    clean = re.sub(r'['']', "'", clean)  # Curly single quotes to standard single quotes
                    file.write(f"{clean}\n\n")

def get_book(sourcefile, flatten_chapters=True):
    """
    Parse a text file into book contents with chapter structure.

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

    with open(sourcefile, "r", encoding="utf-8") as file:
        current_chapter = {"title": "blank", "level": 1, "paragraphs": []}
        initialized_first_chapter = False
        lines_skipped = 0

        for line in file:
            # Handle metadata lines at the start
            if lines_skipped < 2 and (line.startswith("Title") or line.startswith("Author")):
                lines_skipped += 1
                if line.startswith('Title: '):
                    book_title = line.replace('Title: ', '').strip()
                elif line.startswith('Author: '):
                    book_author = line.replace('Author: ', '').strip()
                continue

            line = line.strip()

            # Check for header lines (# ## ### etc.)
            if line.startswith("#"):
                # Count the header level
                header_level = 0
                for char in line:
                    if char == '#':
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
                chapter_title = line.lstrip('#').strip()

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
                    line = ' '.join(cleaned_sentences)
                    current_chapter["paragraphs"].append(line)

        # Append the last chapter if it contains any paragraphs.
        if current_chapter["paragraphs"]:
            book_contents.append(current_chapter)

    return book_contents, book_title, book_author, chapter_titles

def sort_key(s):
    # extract number from the string
    return int(re.findall(r'\d+', s)[0])

def check_for_file(filename):
    if os.path.isfile(filename):
        print(f"The file '{filename}' already exists.")
        overwrite = input("Do you want to overwrite the file? (y/n): ")
        if overwrite.lower() != 'y':
            print("Exiting without overwriting the file.")
            sys.exit()
        else:
            os.remove(filename)

def append_silence(tempfile, duration=1200):
    audio = AudioSegment.from_file(tempfile)
    # Create a silence segment
    silence = AudioSegment.silent(duration)
    # Append the silence segment to the audio
    combined = audio + silence
    # Save the combined audio back to file
    combined.export(tempfile, format="flac")

def read_book(book_contents, speaker, paragraphpause, sentencepause, rate=None, volume=None, pronunciation_processor=None, multi_voice_processor=None):
    """Generate audio for all chapters in a book.

    Args:
        book_contents: List of chapter dicts with 'title' and 'paragraphs'
        speaker: Voice ID (e.g., "en-US-AndrewNeural")
        paragraphpause: Pause duration after paragraphs in milliseconds
        sentencepause: Pause duration after sentences in milliseconds
        rate: Speech rate adjustment (e.g., "+20%", "-10%")
        volume: Volume adjustment (e.g., "+50%", "-25%")
        pronunciation_processor: Optional PronunciationProcessor for custom pronunciations
        multi_voice_processor: Optional MultiVoiceProcessor for different character voices

    Returns:
        List of generated FLAC segment filenames
    """
    segments = []
    # Do not read these into the audio file:
    title_names_to_skip_reading = ['Title', 'blank']

    for i, chapter in enumerate(book_contents, start=1):
        files = []
        partname = f"part{i}.flac"
        print(f"\n\n")

        if os.path.isfile(partname):
            print(f"{partname} exists, skipping to next chapter")
            segments.append(partname)
        else:
            if chapter["title"] in title_names_to_skip_reading:
                print(f"Chapter name: \"{chapter['title']}\"  -  Note: The word \"{chapter['title']}\" will not be read into audio file.")
            else:
                print(f"Chapter name: \"{chapter['title']}\"")

            if chapter["title"] == "":
                chapter["title"] = "blank"
            if chapter["title"] not in title_names_to_skip_reading:
                # Apply pronunciation to chapter title
                title_text = chapter["title"]
                if pronunciation_processor:
                    title_text = pronunciation_processor.process_text(title_text)
                asyncio.run(
                    parallel_edgespeak([title_text], [speaker], ["sntnc0.mp3"], rate, volume)
                )
                append_silence("sntnc0.mp3", 1200)

            for pindex, paragraph in enumerate(
                tqdm(chapter["paragraphs"], desc=f"Generating audio files: ",unit='pg')
            ):
                ptemp = f"pgraphs{pindex}.flac"
                if os.path.isfile(ptemp):
                    print(f"{ptemp} exists, skipping to next paragraph")
                else:
                    # Apply pronunciation processing if available
                    processed_paragraph = paragraph
                    if pronunciation_processor:
                        processed_paragraph = pronunciation_processor.process_text(paragraph)

                    # Handle multi-voice processing
                    if multi_voice_processor:
                        # Get voice-text pairs for multi-voice
                        voice_text_pairs = multi_voice_processor.process_paragraph(processed_paragraph)
                        sentences = [text for _, text in voice_text_pairs]
                        speakers = [voice for voice, _ in voice_text_pairs]
                    else:
                        sentences = sent_tokenize(processed_paragraph)
                        speakers = [speaker] * len(sentences)

                    filenames = [
                        "sntnc" + str(z + 1) + ".mp3" for z in range(len(sentences))
                    ]
                    asyncio.run(parallel_edgespeak(sentences, speakers, filenames, rate, volume))
                    append_silence(filenames[-1], paragraphpause)
                    # combine sentences in paragraph
                    sorted_files = sorted(filenames, key=sort_key)
                    if os.path.exists("sntnc0.mp3"):
                        sorted_files.insert(0, "sntnc0.mp3")
                    combined = AudioSegment.empty()
                    for file in sorted_files:
                        combined += AudioSegment.from_file(file)
                    combined.export(ptemp, format="flac")
                    for file in sorted_files:
                        os.remove(file)
                files.append(ptemp)
            # combine paragraphs into chapter
            append_silence(files[-1], 2000)
            combined = AudioSegment.empty()
            for file in files:
                combined += AudioSegment.from_file(file)
            combined.export(partname, format="flac")
            for file in files:
                os.remove(file)
            segments.append(partname)
    return segments

def generate_metadata(files, author, title, chapter_titles):
    chap = 0
    start_time = 0
    with open("FFMETADATAFILE", "w") as file:
        file.write(";FFMETADATA1\n")
        file.write(f"ARTIST={author}\n")
        file.write(f"ALBUM={title}\n")
        file.write(f"TITLE={title}\n")
        file.write("DESCRIPTION=Made with https://github.com/aedocw/epub2tts-edge\n")
        for file_name in files:
            duration = get_duration(file_name)
            file.write("[CHAPTER]\n")
            file.write("TIMEBASE=1/1000\n")
            file.write(f"START={start_time}\n")
            file.write(f"END={start_time + duration}\n")
            file.write(f"title={chapter_titles[chap]}\n")
            chap += 1
            start_time += duration

def get_duration(file_path):
    audio = AudioSegment.from_file(file_path)
    duration_milliseconds = len(audio)
    return duration_milliseconds

def make_m4b(files, sourcefile, speaker, normalizer=None, silence_detector=None):
    """Create M4B audiobook from chapter files.

    Args:
        files: List of FLAC chapter files
        sourcefile: Source text file path
        speaker: Speaker voice ID
        normalizer: Optional AudioNormalizer instance for volume normalization
        silence_detector: Optional SilenceDetector instance for trimming silence
    """
    import tempfile
    import shutil

    files_to_use = files
    cleanup_dirs = []

    # Apply silence trimming if enabled
    if silence_detector and silence_detector.config.enabled:
        print("\nTrimming excessive silence...")
        silence_temp_dir = tempfile.mkdtemp(prefix="audiobookify_silence_")
        cleanup_dirs.append(silence_temp_dir)

        trimmed_files = silence_detector.trim_files(files_to_use, silence_temp_dir)
        files_to_use = trimmed_files

    # Apply normalization if enabled
    if normalizer and normalizer.config.enabled:
        print("\nNormalizing audio levels...")
        norm_temp_dir = tempfile.mkdtemp(prefix="audiobookify_norm_")
        cleanup_dirs.append(norm_temp_dir)

        # Normalize files with unified gain for consistent volume
        normalized_files = normalizer.normalize_files(files_to_use, norm_temp_dir, unified=True)
        files_to_use = normalized_files

    filelist = "filelist.txt"
    basefile = sourcefile.replace(".txt", "")
    outputm4a = f"{basefile} ({speaker}).m4a"
    outputm4b = f"{basefile} ({speaker}).m4b"
    with open(filelist, "w") as f:
        for filename in files_to_use:
            filename = filename.replace("'", "'\\''")
            f.write(f"file '{filename}'\n")
    ffmpeg_command = [
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        filelist,
        "-codec:a",
        "flac",
        "-f",
        "mp4",
        "-strict",
        "-2",
        outputm4a,
    ]
    subprocess.run(ffmpeg_command)
    ffmpeg_command = [
        "ffmpeg",
        "-i",
        outputm4a,
        "-i",
        "FFMETADATAFILE",
        "-map_metadata",
        "1",
        "-codec",
        "aac",
        outputm4b,
    ]
    subprocess.run(ffmpeg_command)
    os.remove(filelist)
    os.remove("FFMETADATAFILE")
    os.remove(outputm4a)
    for f in files:
        os.remove(f)

    # Clean up temp directories from silence/normalization processing
    for temp_dir in cleanup_dirs:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return outputm4b

def add_cover(cover_img, filename):
    try:
        if os.path.isfile(cover_img):
            m4b = mp4.MP4(filename)
            cover_image = open(cover_img, "rb").read()
            m4b["covr"] = [mp4.MP4Cover(cover_image)]
            m4b.save()
        else:
            print(f"Cover image {cover_img} not found")
    except:
        print(f"Cover image {cover_img} not found")

def run_edgespeak(sentence, speaker, filename, rate=None, volume=None):
    """Generate speech for a sentence using edge-tts.

    Args:
        sentence: Text to speak
        speaker: Voice ID (e.g., "en-US-AndrewNeural")
        filename: Output MP3 filename
        rate: Speech rate adjustment (e.g., "+20%", "-10%")
        volume: Volume adjustment (e.g., "+50%", "-25%")
    """
    for speakattempt in range(3):
        try:
            # Build kwargs for edge_tts
            kwargs = {}
            if rate:
                kwargs["rate"] = rate
            if volume:
                kwargs["volume"] = volume

            communicate = edge_tts.Communicate(sentence, speaker, **kwargs)
            run_save(communicate, filename)
            if os.path.getsize(filename) == 0:
                raise Exception("Failed to save file from edge_tts")
            break
        except Exception as e:
            print(f"Attempt {speakattempt+1}/3 failed with '{sentence}' in run_edgespeak with error: {e}")
            # wait a few seconds in case its a transient network issue
            time.sleep(3)
    else:
        print(f"Giving up on sentence '{sentence}' after 3 attempts in run_edgespeak.")
        exit()

def run_save(communicate, filename):
    asyncio.run(communicate.save(filename))

async def parallel_edgespeak(sentences, speakers, filenames, rate=None, volume=None):
    """Generate speech for multiple sentences in parallel.

    Args:
        sentences: List of texts to speak
        speakers: List of voice IDs
        filenames: List of output filenames
        rate: Speech rate adjustment (e.g., "+20%", "-10%")
        volume: Volume adjustment (e.g., "+50%", "-25%")
    """
    semaphore = asyncio.Semaphore(10)  # Limit the number of concurrent tasks

    with concurrent.futures.ThreadPoolExecutor() as executor:
        tasks = []
        for sentence, speaker, filename in zip(sentences, speakers, filenames):
            async with semaphore:
                loop = asyncio.get_running_loop()
                sentence = re.sub(r'[!]+', '!', sentence)
                sentence = re.sub(r'[?]+', '?', sentence)
                task = loop.run_in_executor(
                    executor, run_edgespeak, sentence, speaker, filename, rate, volume
                )
                tasks.append(task)
        await asyncio.gather(*tasks)


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
        """
    )
    parser.add_argument("sourcefile", type=str, nargs='?', default=None,
                        help="EPUB file, text file, or directory to process")
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
        help="Duration of pause after sentence, in milliseconds (default: 1200)"
    )
    parser.add_argument(
        "--paragraphpause",
        type=int,
        default=1200,
        help="Duration of pause after paragraph, in milliseconds (default: 1200)"
    )

    # Enhanced chapter detection options
    parser.add_argument(
        "--detect",
        type=str,
        choices=["toc", "headings", "combined", "auto"],
        default="combined",
        help="Chapter detection method (default: combined)"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum chapter depth to include (default: all levels)"
    )
    parser.add_argument(
        "--hierarchy",
        type=str,
        choices=["flat", "numbered", "indented", "arrow", "breadcrumb"],
        default="flat",
        help="How to display chapter hierarchy in output (default: flat)"
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use legacy chapter detection (original algorithm)"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview detected chapters without exporting (EPUB only)"
    )

    # Batch processing options
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Enable batch processing mode for directories"
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Recursively scan subdirectories for EPUBs (batch mode)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Output directory for processed files (batch mode)"
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Only export EPUBs to text, don't convert to audio (batch mode)"
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Process all files, don't skip already processed (batch mode)"
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop batch processing if any book fails"
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Launch the interactive Terminal UI"
    )

    # Voice preview options
    parser.add_argument(
        "--preview-voice",
        action="store_true",
        help="Generate a voice preview sample for the selected speaker"
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available voice options with details"
    )
    parser.add_argument(
        "--rate",
        type=str,
        default=None,
        help="Speech rate adjustment (e.g., '+20%%', '-10%%')"
    )
    parser.add_argument(
        "--volume",
        type=str,
        default=None,
        help="Volume adjustment (e.g., '+50%%', '-25%%')"
    )
    parser.add_argument(
        "--chapters",
        type=str,
        default=None,
        help="Select specific chapters to convert (e.g., '1-5', '1,3,7', '5-')"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous incomplete conversion"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Start fresh, ignore any saved progress"
    )

    # Audio normalization options
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="Normalize audio for consistent volume across chapters"
    )
    parser.add_argument(
        "--normalize-target",
        type=float,
        default=-16.0,
        help="Target loudness in dBFS for normalization (default: -16.0)"
    )
    parser.add_argument(
        "--normalize-method",
        type=str,
        choices=["peak", "rms"],
        default="peak",
        help="Normalization method: 'peak' or 'rms' (default: peak)"
    )

    # Silence detection options
    parser.add_argument(
        "--trim-silence",
        action="store_true",
        help="Trim excessive silence from audio"
    )
    parser.add_argument(
        "--silence-thresh",
        type=int,
        default=-40,
        help="Silence threshold in dBFS (default: -40)"
    )
    parser.add_argument(
        "--max-silence",
        type=int,
        default=2000,
        help="Maximum silence duration in ms before trimming (default: 2000)"
    )

    # Pronunciation dictionary options
    parser.add_argument(
        "--pronunciation",
        type=str,
        default=None,
        help="Path to pronunciation dictionary file (JSON or text format)"
    )
    parser.add_argument(
        "--pronunciation-case-sensitive",
        action="store_true",
        help="Make pronunciation replacements case-sensitive"
    )

    # Multi-voice options
    parser.add_argument(
        "--voice-mapping",
        type=str,
        default=None,
        help="Path to voice mapping file (JSON) for multi-voice support"
    )
    parser.add_argument(
        "--narrator-voice",
        type=str,
        default=None,
        help="Voice to use for narration (non-dialogue text)"
    )

    args = parser.parse_args()

    # Handle voice listing
    if args.list_voices:
        from .voice_preview import AVAILABLE_VOICES
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
        from .voice_preview import VoicePreview, VoicePreviewConfig
        import subprocess
        import shutil

        config = VoicePreviewConfig(speaker=args.speaker)
        if args.rate:
            config.rate = args.rate
        if args.volume:
            config.volume = args.volume

        preview = VoicePreview(config)
        print(f"\nGenerating voice preview for: {args.speaker}")
        if args.rate:
            print(f"  Rate: {args.rate}")
        if args.volume:
            print(f"  Volume: {args.volume}")

        try:
            output_path = preview.generate_preview_temp()
            print(f"\nPreview saved to: {output_path}")

            # Try to play the audio if a player is available
            players = ['ffplay', 'mpv', 'vlc', 'afplay', 'aplay']
            player_found = False
            for player in players:
                if shutil.which(player):
                    print(f"Playing with {player}...")
                    try:
                        if player == 'ffplay':
                            subprocess.run([player, '-nodisp', '-autoexit', output_path],
                                         capture_output=True, timeout=30)
                        else:
                            subprocess.run([player, output_path],
                                         capture_output=True, timeout=30)
                        player_found = True
                        break
                    except subprocess.TimeoutExpired:
                        pass
                    except Exception:
                        continue

            if not player_found:
                print("\nNo audio player found. You can play the file manually:")
                print(f"  {output_path}")

        except Exception as e:
            print(f"\nError generating preview: {e}")
            return

        return

    # Launch TUI if requested
    if args.tui:
        from .tui import main as tui_main
        tui_main(args.sourcefile or ".")
        return

    # Validate sourcefile is provided for remaining operations
    if not args.sourcefile:
        parser.error("sourcefile is required (use --list-voices or --preview-voice for voice options without a file)")

    print(args)

    ensure_punkt()

    # Check if batch mode or directory input
    is_directory = os.path.isdir(args.sourcefile)

    if args.batch or is_directory:
        # Batch processing mode
        from .batch_processor import BatchProcessor, BatchConfig

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
            print(f"\nReport saved to: {report_path}")

        return

    # If we get an epub, export that to txt file, then exit
    if args.sourcefile.endswith(".epub"):
        book = epub.read_epub(args.sourcefile)

        # Preview mode - just show detected structure
        if args.preview:
            print("\nPreviewing chapter detection...\n")
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
                hierarchy_style=style_enum
            )
            detector.detect()
            print("Detected chapter structure:")
            detector.print_structure()

            # Show summary
            chapters = detector.get_flat_chapters()
            total_paragraphs = sum(len(c['paragraphs']) for c in chapters)
            print(f"\nSummary: {len(chapters)} chapters, {total_paragraphs} paragraphs")
            exit()

        # Use legacy or enhanced export
        if args.legacy:
            export_legacy(book, args.sourcefile)
        else:
            export(
                book,
                args.sourcefile,
                detection_method=args.detect,
                max_depth=args.max_depth,
                hierarchy_style=args.hierarchy
            )
        exit()

    # Process text file to audiobook
    book_contents, book_title, book_author, chapter_titles = get_book(args.sourcefile)

    # Apply chapter selection if specified
    if args.chapters:
        from .chapter_selector import ChapterSelector
        selector = ChapterSelector(args.chapters)
        print(f"\n{selector.get_summary()}")

        # Filter book_contents and chapter_titles together
        selected_indices = selector.get_selected_indices(len(book_contents))
        book_contents = [book_contents[i] for i in selected_indices]
        chapter_titles = [chapter_titles[i] for i in selected_indices]

        if not book_contents:
            print("Error: No chapters match the selection")
            return
        print(f"Processing {len(book_contents)} selected chapters\n")

    # State management for pause/resume
    from .pause_resume import StateManager, ConversionState
    output_dir = os.path.dirname(os.path.abspath(args.sourcefile)) or "."
    state_manager = StateManager(output_dir)

    # Check for existing state
    if not args.no_resume and state_manager.has_state():
        state = state_manager.load_state()
        if state and state_manager.state_matches(args.sourcefile):
            if state.is_resumable:
                # Check for existing intermediate files
                existing_parts = [f for f in [f"part{i}.flac" for i in range(1, len(book_contents)+1)]
                                if os.path.isfile(f)]
                if existing_parts:
                    print(f"\nResuming conversion: {len(existing_parts)}/{len(book_contents)} chapters completed")
                    if not args.resume:
                        print("  (use --no-resume to start fresh)")

    # Save state before starting
    state = ConversionState(
        source_file=os.path.abspath(args.sourcefile),
        total_chapters=len(book_contents),
        completed_chapters=0,
        speaker=args.speaker,
        rate=args.rate,
        volume=args.volume,
        chapters_selection=args.chapters
    )
    state_manager.save_state(state)

    # Set up audio normalizer if requested
    normalizer = None
    if args.normalize:
        from .audio_normalization import AudioNormalizer, NormalizationConfig
        normalizer = AudioNormalizer(NormalizationConfig(
            target_dbfs=args.normalize_target,
            method=args.normalize_method,
            enabled=True
        ))
        print(f"\nAudio normalization enabled: {args.normalize_method} method, target {args.normalize_target} dBFS")

    # Set up silence detector if requested
    silence_detector = None
    if args.trim_silence:
        from .silence_detection import SilenceDetector, SilenceConfig
        silence_detector = SilenceDetector(SilenceConfig(
            silence_thresh=args.silence_thresh,
            max_silence_len=args.max_silence,
            enabled=True
        ))
        print(f"\nSilence trimming enabled: threshold {args.silence_thresh} dBFS, max {args.max_silence}ms")

    # Set up pronunciation processor if dictionary provided
    pronunciation_processor = None
    if args.pronunciation:
        from .pronunciation import PronunciationProcessor, PronunciationConfig
        pronunciation_processor = PronunciationProcessor(PronunciationConfig(
            case_sensitive=args.pronunciation_case_sensitive
        ))
        try:
            pronunciation_processor.load_dictionary(args.pronunciation)
            print(f"\nPronunciation dictionary loaded: {pronunciation_processor.entry_count} entries")
        except FileNotFoundError:
            print(f"\nWarning: Pronunciation dictionary not found: {args.pronunciation}")
            pronunciation_processor = None
        except Exception as e:
            print(f"\nWarning: Error loading pronunciation dictionary: {e}")
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
                print(f"\nMulti-voice enabled: {multi_voice_processor.character_count} character voices loaded")
            except FileNotFoundError:
                print(f"\nWarning: Voice mapping file not found: {args.voice_mapping}")
                multi_voice_processor = None
            except Exception as e:
                print(f"\nWarning: Error loading voice mapping: {e}")
                multi_voice_processor = None
        elif args.narrator_voice:
            print(f"\nMulti-voice enabled: narrator voice set to {args.narrator_voice}")

    try:
        files = read_book(book_contents, args.speaker, args.paragraphpause, args.sentencepause,
                          rate=args.rate, volume=args.volume,
                          pronunciation_processor=pronunciation_processor,
                          multi_voice_processor=multi_voice_processor)
        generate_metadata(files, book_author, book_title, chapter_titles)
        m4bfilename = make_m4b(files, args.sourcefile, args.speaker,
                               normalizer=normalizer, silence_detector=silence_detector)

        # Handle cover image
        cover_path = args.cover
        if not cover_path:
            # Try to find cover with same name as source file
            base_name = args.sourcefile.replace(".txt", "")
            for ext in ['.png', '.jpg', '.jpeg']:
                potential_cover = base_name + ext
                if os.path.isfile(potential_cover):
                    cover_path = potential_cover
                    print(f"Found cover image: {cover_path}")
                    break

        if cover_path:
            add_cover(cover_path, m4bfilename)

        # Clear state on successful completion
        state_manager.clear_state()

        print(f"\nAudiobook created: {m4bfilename}")

    except KeyboardInterrupt:
        print("\n\nConversion paused. Run with --resume to continue.")
        # State is already saved, intermediate files preserved
        return
    except Exception as e:
        print(f"\nError during conversion: {e}")
        print("Intermediate files preserved. Run with --resume to continue.")
        raise


if __name__ == "__main__":
    main()
