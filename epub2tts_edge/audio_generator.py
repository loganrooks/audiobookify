"""Audio generation module for audiobookify.

This module handles text-to-speech conversion using Microsoft Edge TTS,
audio file manipulation, and M4B audiobook creation.
"""

import asyncio
import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

import edge_tts
from mutagen import mp4
from nltk.tokenize import sent_tokenize
from pydub import AudioSegment
from tqdm import tqdm

from .logger import get_logger

# Module logger
logger = get_logger(__name__)

# Default configuration
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 3  # seconds
DEFAULT_CONCURRENT_TASKS = 10


def sort_key(s: str) -> int:
    """Extract number from filename for sorting.

    Args:
        s: Filename string like 'sntnc1.mp3'

    Returns:
        Integer extracted from the filename
    """
    return int(re.findall(r'\d+', s)[0])


def append_silence(tempfile_path: str, duration: int = 1200) -> None:
    """Append silence to an audio file.

    Args:
        tempfile_path: Path to the audio file
        duration: Duration of silence in milliseconds (default 1200ms)
    """
    audio = AudioSegment.from_file(tempfile_path)
    silence = AudioSegment.silent(duration)
    combined = audio + silence
    combined.export(tempfile_path, format="flac")


def get_duration(file_path: str) -> int:
    """Get duration of an audio file in milliseconds.

    Args:
        file_path: Path to the audio file

    Returns:
        Duration in milliseconds
    """
    audio = AudioSegment.from_file(file_path)
    return len(audio)


def generate_metadata(
    files: list[str],
    author: str,
    title: str,
    chapter_titles: list[str]
) -> None:
    """Generate FFmpeg metadata file for M4B chapters.

    Args:
        files: List of audio file paths
        author: Book author name
        title: Book title
        chapter_titles: List of chapter titles
    """
    chap = 0
    start_time = 0
    with open("FFMETADATAFILE", "w", encoding="utf-8") as file:
        file.write(";FFMETADATA1\n")
        file.write(f"ARTIST={author}\n")
        file.write(f"ALBUM={title}\n")
        file.write(f"TITLE={title}\n")
        file.write("DESCRIPTION=Made with https://github.com/loganrooks/audiobookify\n")
        for file_name in files:
            duration = get_duration(file_name)
            file.write("[CHAPTER]\n")
            file.write("TIMEBASE=1/1000\n")
            file.write(f"START={start_time}\n")
            file.write(f"END={start_time + duration}\n")
            file.write(f"title={chapter_titles[chap]}\n")
            chap += 1
            start_time += duration


def run_save(communicate: edge_tts.Communicate, filename: str) -> None:
    """Save edge-tts output to file.

    Args:
        communicate: edge_tts Communicate instance
        filename: Output filename
    """
    asyncio.run(communicate.save(filename))


def run_edgespeak(
    sentence: str,
    speaker: str,
    filename: str,
    rate: str | None = None,
    volume: str | None = None,
    retry_count: int = DEFAULT_RETRY_COUNT,
    retry_delay: int = DEFAULT_RETRY_DELAY
) -> None:
    """Generate speech for a sentence using edge-tts.

    Args:
        sentence: Text to speak
        speaker: Voice ID (e.g., "en-US-AndrewNeural")
        filename: Output MP3 filename
        rate: Speech rate adjustment (e.g., "+20%", "-10%")
        volume: Volume adjustment (e.g., "+50%", "-25%")
        retry_count: Number of retry attempts (default 3)
        retry_delay: Delay between retries in seconds (default 3)

    Raises:
        SystemExit: If all retry attempts fail
    """
    for speakattempt in range(retry_count):
        try:
            kwargs = {}
            if rate:
                kwargs["rate"] = rate
            if volume:
                kwargs["volume"] = volume

            communicate = edge_tts.Communicate(sentence, speaker, **kwargs)
            run_save(communicate, filename)
            if os.path.getsize(filename) == 0:
                raise RuntimeError("Failed to save file from edge_tts - empty file")
            break
        except Exception as e:
            logger.warning(
                "Attempt %d/%d failed for '%s...': %s",
                speakattempt + 1, retry_count, sentence[:50], e
            )
            if speakattempt < retry_count - 1:
                time.sleep(retry_delay)
    else:
        logger.error(
            "Giving up on sentence after %d attempts: '%s...'",
            retry_count, sentence[:50]
        )
        sys.exit(1)


async def parallel_edgespeak(
    sentences: list[str],
    speakers: list[str],
    filenames: list[str],
    rate: str | None = None,
    volume: str | None = None,
    max_concurrent: int = DEFAULT_CONCURRENT_TASKS,
    retry_count: int = DEFAULT_RETRY_COUNT,
    retry_delay: int = DEFAULT_RETRY_DELAY
) -> None:
    """Generate speech for multiple sentences in parallel.

    Args:
        sentences: List of texts to speak
        speakers: List of voice IDs
        filenames: List of output filenames
        rate: Speech rate adjustment (e.g., "+20%", "-10%")
        volume: Volume adjustment (e.g., "+50%", "-25%")
        max_concurrent: Maximum concurrent TTS tasks (default 10)
        retry_count: Number of retry attempts per sentence (default 3)
        retry_delay: Delay between retries in seconds (default 3)
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        tasks = []
        for sentence, speaker, filename in zip(sentences, speakers, filenames, strict=False):
            async with semaphore:
                loop = asyncio.get_running_loop()
                # Clean up excessive punctuation
                sentence = re.sub(r'[!]+', '!', sentence)
                sentence = re.sub(r'[?]+', '?', sentence)
                task = loop.run_in_executor(
                    executor, run_edgespeak, sentence, speaker, filename,
                    rate, volume, retry_count, retry_delay
                )
                tasks.append(task)
        await asyncio.gather(*tasks)


def read_book(
    book_contents: list[dict],
    speaker: str,
    paragraphpause: int,
    sentencepause: int,
    rate: str | None = None,
    volume: str | None = None,
    pronunciation_processor=None,
    multi_voice_processor=None,
    retry_count: int = DEFAULT_RETRY_COUNT,
    retry_delay: int = DEFAULT_RETRY_DELAY
) -> list[str]:
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
        retry_count: Number of retry attempts for TTS (default 3)
        retry_delay: Delay between retries in seconds (default 3)

    Returns:
        List of generated FLAC segment filenames
    """
    segments = []
    title_names_to_skip_reading = ['Title', 'blank']

    for i, chapter in enumerate(book_contents, start=1):
        files = []
        partname = f"part{i}.flac"

        if os.path.isfile(partname):
            logger.info("%s exists, skipping to next chapter", partname)
            segments.append(partname)
        else:
            if chapter["title"] in title_names_to_skip_reading:
                logger.debug("Chapter name: '%s' - will not be read into audio", chapter['title'])
            else:
                logger.info("Processing chapter: '%s'", chapter['title'])

            if chapter["title"] == "":
                chapter["title"] = "blank"
            if chapter["title"] not in title_names_to_skip_reading:
                title_text = chapter["title"]
                if pronunciation_processor:
                    title_text = pronunciation_processor.process_text(title_text)
                asyncio.run(
                    parallel_edgespeak(
                        [title_text], [speaker], ["sntnc0.mp3"],
                        rate, volume, retry_count=retry_count, retry_delay=retry_delay
                    )
                )
                append_silence("sntnc0.mp3", 1200)

            for pindex, paragraph in enumerate(
                tqdm(chapter["paragraphs"], desc="Generating audio: ", unit='pg')
            ):
                ptemp = f"pgraphs{pindex}.flac"
                if os.path.isfile(ptemp):
                    logger.debug("%s exists, skipping to next paragraph", ptemp)
                else:
                    processed_paragraph = paragraph
                    if pronunciation_processor:
                        processed_paragraph = pronunciation_processor.process_text(paragraph)

                    if multi_voice_processor:
                        voice_text_pairs = multi_voice_processor.process_paragraph(processed_paragraph)
                        sentences = [text for _, text in voice_text_pairs]
                        speakers = [voice for voice, _ in voice_text_pairs]
                    else:
                        sentences = sent_tokenize(processed_paragraph)
                        speakers = [speaker] * len(sentences)

                    filenames = [f"sntnc{z + 1}.mp3" for z in range(len(sentences))]
                    asyncio.run(
                        parallel_edgespeak(
                            sentences, speakers, filenames,
                            rate, volume, retry_count=retry_count, retry_delay=retry_delay
                        )
                    )
                    append_silence(filenames[-1], paragraphpause)

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

            append_silence(files[-1], 2000)
            combined = AudioSegment.empty()
            for file in files:
                combined += AudioSegment.from_file(file)
            combined.export(partname, format="flac")
            for file in files:
                os.remove(file)
            segments.append(partname)
    return segments


def make_m4b(
    files: list[str],
    sourcefile: str,
    speaker: str,
    normalizer=None,
    silence_detector=None
) -> str:
    """Create M4B audiobook from chapter files.

    Args:
        files: List of FLAC chapter files
        sourcefile: Source text file path
        speaker: Speaker voice ID
        normalizer: Optional AudioNormalizer instance for volume normalization
        silence_detector: Optional SilenceDetector instance for trimming silence

    Returns:
        Path to the created M4B file
    """
    files_to_use = files
    cleanup_dirs = []

    # Apply silence trimming if enabled
    if silence_detector and silence_detector.config.enabled:
        logger.info("Trimming excessive silence...")
        silence_temp_dir = tempfile.mkdtemp(prefix="audiobookify_silence_")
        cleanup_dirs.append(silence_temp_dir)
        trimmed_files = silence_detector.trim_files(files_to_use, silence_temp_dir)
        files_to_use = trimmed_files

    # Apply normalization if enabled
    if normalizer and normalizer.config.enabled:
        logger.info("Normalizing audio levels...")
        norm_temp_dir = tempfile.mkdtemp(prefix="audiobookify_norm_")
        cleanup_dirs.append(norm_temp_dir)
        normalized_files = normalizer.normalize_files(files_to_use, norm_temp_dir, unified=True)
        files_to_use = normalized_files

    filelist = "filelist.txt"
    basefile = sourcefile.replace(".txt", "")
    outputm4a = f"{basefile} ({speaker}).m4a"
    outputm4b = f"{basefile} ({speaker}).m4b"

    with open(filelist, "w", encoding="utf-8") as f:
        for filename in files_to_use:
            # Escape single quotes for ffmpeg
            filename = filename.replace("'", "'\\''")
            f.write(f"file '{filename}'\n")

    # Concatenate audio files
    ffmpeg_command = [
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", filelist, "-codec:a", "flac",
        "-f", "mp4", "-strict", "-2", outputm4a,
    ]
    subprocess.run(ffmpeg_command, check=True)

    # Add metadata and convert to AAC
    ffmpeg_command = [
        "ffmpeg", "-i", outputm4a, "-i", "FFMETADATAFILE",
        "-map_metadata", "1", "-codec", "aac", outputm4b,
    ]
    subprocess.run(ffmpeg_command, check=True)

    # Cleanup
    os.remove(filelist)
    os.remove("FFMETADATAFILE")
    os.remove(outputm4a)
    for f in files:
        os.remove(f)

    for temp_dir in cleanup_dirs:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return outputm4b


def add_cover(cover_img: str, filename: str) -> bool:
    """Add cover image to M4B file.

    Args:
        cover_img: Path to cover image file
        filename: Path to M4B file

    Returns:
        True if cover was added successfully, False otherwise
    """
    try:
        if os.path.isfile(cover_img):
            m4b = mp4.MP4(filename)
            with open(cover_img, "rb") as f:
                cover_image = f.read()
            m4b["covr"] = [mp4.MP4Cover(cover_image)]
            m4b.save()
            logger.info("Cover image added to %s", filename)
            return True
        else:
            logger.warning("Cover image not found: %s", cover_img)
            return False
    except OSError as e:
        logger.warning("Could not add cover image %s: %s", cover_img, e)
        return False
    except Exception as e:
        logger.error("Unexpected error adding cover image: %s", e)
        return False
