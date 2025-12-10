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
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

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
DEFAULT_RETRY_DELAY = 2  # seconds (base delay for exponential backoff)
DEFAULT_CONCURRENT_TASKS = 5  # Parallel TTS tasks (safe with edge-tts <7.1.0)
AUTH_ERROR_COOLDOWN = 30  # seconds to wait before final retry on auth/SSL errors


@dataclass
class ProgressInfo:
    """Progress information for callbacks."""

    chapter_num: int
    total_chapters: int
    chapter_title: str
    paragraph_num: int
    total_paragraphs: int
    status: str  # "chapter_start", "paragraph", "chapter_done"


# Type alias for progress callback
ProgressCallback = Callable[[ProgressInfo], None]


def sort_key(s: str) -> int:
    """Extract number from filename for sorting.

    Args:
        s: Filename string like 'sntnc1.mp3'

    Returns:
        Integer extracted from the filename
    """
    return int(re.findall(r"\d+", s)[0])


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
    chapter_titles: list[str],
    output_dir: str | None = None,
) -> str:
    """Generate FFmpeg metadata file for M4B chapters.

    Args:
        files: List of audio file paths
        author: Book author name
        title: Book title
        chapter_titles: List of chapter titles
        output_dir: Optional directory for metadata file. If None, uses current directory.

    Returns:
        Path to the generated metadata file
    """
    if output_dir:
        metadata_path = os.path.join(output_dir, "FFMETADATAFILE")
    else:
        metadata_path = "FFMETADATAFILE"

    chap = 0
    start_time = 0
    with open(metadata_path, "w", encoding="utf-8") as file:
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

    return metadata_path


def run_save(communicate: edge_tts.Communicate, filename: str) -> None:
    """Save edge-tts output to file.

    Args:
        communicate: edge_tts Communicate instance
        filename: Output filename
    """
    asyncio.run(communicate.save(filename))


class TTSGenerationError(Exception):
    """Raised when TTS generation fails after all retry attempts."""

    pass


def _is_auth_or_ssl_error(error: Exception) -> bool:
    """Check if an error is an authentication/SSL error (401, 429, etc.).

    Note: 401 errors from edge-tts are typically caused by SSL fingerprinting
    issues in edge-tts versions >= 7.1.0, not actual rate limiting.
    """
    error_str = str(error).lower()
    return any(
        code in error_str
        for code in ["401", "429", "rate limit", "too many requests", "ssl", "handshake"]
    )


def run_edgespeak(
    sentence: str,
    speaker: str,
    filename: str,
    rate: str | None = None,
    volume: str | None = None,
    retry_count: int = DEFAULT_RETRY_COUNT,
    retry_delay: int = DEFAULT_RETRY_DELAY,
) -> None:
    """Generate speech for a sentence using edge-tts.

    Uses exponential backoff for retries, with special handling for auth/SSL
    errors (401, 429) which get an additional cooldown retry.

    Note: 401 errors are typically caused by SSL fingerprinting issues in
    edge-tts >= 7.1.0. Ensure edge-tts version is < 7.1.0.

    Args:
        sentence: Text to speak
        speaker: Voice ID (e.g., "en-US-AndrewNeural")
        filename: Output MP3 filename
        rate: Speech rate adjustment (e.g., "+20%", "-10%")
        volume: Volume adjustment (e.g., "+50%", "-25%")
        retry_count: Number of retry attempts (default 3)
        retry_delay: Base delay between retries in seconds (default 2, doubles each retry)

    Raises:
        TTSGenerationError: If all retry attempts fail
    """
    last_error = None
    is_auth_error = False

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
            return  # Success!
        except Exception as e:
            last_error = e
            is_auth_error = _is_auth_or_ssl_error(e)

            logger.warning(
                "Attempt %d/%d failed for '%s...': %s",
                speakattempt + 1,
                retry_count,
                sentence[:50],
                e,
            )
            if speakattempt < retry_count - 1:
                # Exponential backoff: 2s, 4s, 8s, ...
                wait_time = retry_delay * (2**speakattempt)
                logger.info("Waiting %d seconds before retry...", wait_time)
                time.sleep(wait_time)

    # If auth/SSL error, try one more time after a longer cooldown
    if is_auth_error:
        logger.warning(
            "Auth/SSL error detected. Waiting %d seconds for cooldown before final attempt...",
            AUTH_ERROR_COOLDOWN,
        )
        time.sleep(AUTH_ERROR_COOLDOWN)
        try:
            kwargs = {}
            if rate:
                kwargs["rate"] = rate
            if volume:
                kwargs["volume"] = volume
            communicate = edge_tts.Communicate(sentence, speaker, **kwargs)
            run_save(communicate, filename)
            if os.path.getsize(filename) > 0:
                logger.info("Cooldown retry succeeded!")
                return  # Success after cooldown!
        except Exception as e:
            last_error = e
            logger.error("Cooldown retry also failed: %s", e)

    # All attempts exhausted
    logger.error("Giving up on sentence after all attempts: '%s...'", sentence[:50])

    # Build helpful error message
    error_msg = f"Failed to generate TTS for: '{sentence[:50]}...'. Last error: {last_error}"
    if is_auth_error:
        error_msg += (
            "\n\nThis appears to be an authentication/SSL error from Microsoft's TTS service. "
            "This is typically caused by edge-tts version incompatibility.\n\n"
            "Suggestions:\n"
            "  1. Check edge-tts version: pip show edge-tts\n"
            "  2. If version >= 7.1.0, downgrade: pip install 'edge-tts>=6.1.0,<7.1.0'\n"
            '  3. Verify connectivity: python -c "import edge_tts; print(edge_tts.__version__)"\n'
            "  4. Run TTS test: pytest tests/test_tts_connectivity.py -v"
        )

    raise TTSGenerationError(error_msg)


async def parallel_edgespeak(
    sentences: list[str],
    speakers: list[str],
    filenames: list[str],
    rate: str | None = None,
    volume: str | None = None,
    max_concurrent: int = DEFAULT_CONCURRENT_TASKS,
    retry_count: int = DEFAULT_RETRY_COUNT,
    retry_delay: int = DEFAULT_RETRY_DELAY,
) -> None:
    """Generate speech for multiple sentences in parallel.

    Uses a shared thread pool and semaphore to limit concurrent TTS requests.
    Requires edge-tts version < 7.1.0 to avoid SSL fingerprinting issues.

    Args:
        sentences: List of texts to speak
        speakers: List of voice IDs
        filenames: List of output filenames
        rate: Speech rate adjustment (e.g., "+20%", "-10%")
        volume: Volume adjustment (e.g., "+50%", "-25%")
        max_concurrent: Maximum concurrent TTS tasks (default 5)
        retry_count: Number of retry attempts per sentence (default 3)
        retry_delay: Delay between retries in seconds (default 2)
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    loop = asyncio.get_running_loop()

    async def limited_edgespeak(
        sentence: str, speaker: str, filename: str, executor: concurrent.futures.Executor
    ) -> None:
        """Run TTS with semaphore limiting concurrency."""
        async with semaphore:
            # Clean up excessive punctuation
            sentence = re.sub(r"[!]+", "!", sentence)
            sentence = re.sub(r"[?]+", "?", sentence)
            await loop.run_in_executor(
                executor,
                run_edgespeak,
                sentence,
                speaker,
                filename,
                rate,
                volume,
                retry_count,
                retry_delay,
            )

    # Use a single shared executor for all tasks
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        tasks = [
            limited_edgespeak(sentence, speaker, filename, executor)
            for sentence, speaker, filename in zip(sentences, speakers, filenames, strict=False)
        ]
        await asyncio.gather(*tasks)


def clean_intermediate_files(output_dir: str | Path) -> None:
    """Remove intermediate audio files from directory.

    This is called before generating audio to ensure no stale files
    from previous jobs can be accidentally reused.

    Args:
        output_dir: Directory containing intermediate files
    """
    out_path = Path(output_dir)
    patterns = ["part*.flac", "pgraphs*.flac", "sntnc*.mp3"]
    for pattern in patterns:
        for f in out_path.glob(pattern):
            try:
                f.unlink()
                logger.debug("Cleaned up intermediate file: %s", f)
            except OSError as e:
                logger.warning("Failed to remove intermediate file %s: %s", f, e)


def read_book(
    book_contents: list[dict],
    speaker: str,
    paragraphpause: int,
    sentencepause: int,
    output_dir: str,
    rate: str | None = None,
    volume: str | None = None,
    pronunciation_processor=None,
    multi_voice_processor=None,
    retry_count: int = DEFAULT_RETRY_COUNT,
    retry_delay: int = DEFAULT_RETRY_DELAY,
    max_concurrent: int = DEFAULT_CONCURRENT_TASKS,
    progress_callback: ProgressCallback | None = None,
    cancellation_check: Callable | None = None,
    skip_completed: int = 0,
) -> list[str]:
    """Generate audio for all chapters in a book.

    IMPORTANT: output_dir MUST be a job's audio directory from JobManager.
    This ensures proper isolation - each job has its own directory, and files
    in that directory belong to that job. Source file validation via hash
    is handled by JobManager before calling this function.

    Args:
        book_contents: List of chapter dicts with 'title' and 'paragraphs'
        speaker: Voice ID (e.g., "en-US-AndrewNeural")
        paragraphpause: Pause duration after paragraphs in milliseconds
        sentencepause: Pause duration after sentences in milliseconds
        output_dir: REQUIRED. Must be a job's audio directory for isolation.
        rate: Speech rate adjustment (e.g., "+20%", "-10%")
        volume: Volume adjustment (e.g., "+50%", "-25%")
        pronunciation_processor: Optional PronunciationProcessor for custom pronunciations
        multi_voice_processor: Optional MultiVoiceProcessor for different character voices
        retry_count: Number of retry attempts for TTS (default 3)
        retry_delay: Delay between retries in seconds (default 3)
        max_concurrent: Max concurrent TTS requests (default 1 for sequential)
        progress_callback: Optional callback for progress updates
        cancellation_check: Optional callable that returns True if processing should stop
        skip_completed: Number of chapters already completed (for resume). Files for
            chapters 1..skip_completed are trusted to exist in output_dir.

    Returns:
        List of generated FLAC segment filenames (absolute paths)
    """
    segments = []
    title_names_to_skip_reading = ["Title", "blank"]
    total_chapters = len(book_contents)

    # output_dir is required - it should be a job's audio directory
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for i, chapter in enumerate(book_contents, start=1):
        # Check for cancellation at chapter start
        if cancellation_check and cancellation_check():
            logger.info("Processing cancelled by user at chapter %d", i)
            return segments
        files = []
        partname = str(out_path / f"part{i}.flac")
        total_paragraphs = len(chapter.get("paragraphs", []))

        # Report chapter start
        if progress_callback:
            progress_callback(
                ProgressInfo(
                    chapter_num=i,
                    total_chapters=total_chapters,
                    chapter_title=chapter.get("title", ""),
                    paragraph_num=0,
                    total_paragraphs=total_paragraphs,
                    status="chapter_start",
                )
            )

        # Resume logic: skip chapters that were already completed in this job
        # The caller (via JobManager) has validated the source file hasn't changed
        if i <= skip_completed and os.path.isfile(partname):
            logger.info("Resuming: chapter %d already completed, reusing %s", i, partname)
            segments.append(partname)
        else:
            # Generate new audio for this chapter
            if chapter["title"] in title_names_to_skip_reading:
                logger.debug("Chapter name: '%s' - will not be read into audio", chapter["title"])
            else:
                logger.info("Processing chapter: '%s'", chapter["title"])

            if chapter["title"] == "":
                chapter["title"] = "blank"
            if chapter["title"] not in title_names_to_skip_reading:
                title_text = chapter["title"]
                if pronunciation_processor:
                    title_text = pronunciation_processor.process_text(title_text)
                title_audio = str(out_path / "sntnc0.mp3")
                asyncio.run(
                    parallel_edgespeak(
                        [title_text],
                        [speaker],
                        [title_audio],
                        rate,
                        volume,
                        max_concurrent=max_concurrent,
                        retry_count=retry_count,
                        retry_delay=retry_delay,
                    )
                )
                append_silence(title_audio, 1200)

            for pindex, paragraph in enumerate(
                tqdm(chapter["paragraphs"], desc="Generating audio: ", unit="pg")
            ):
                # Check for cancellation at paragraph start
                if cancellation_check and cancellation_check():
                    logger.info(
                        "Processing cancelled by user at chapter %d, paragraph %d",
                        i,
                        pindex + 1,
                    )
                    return segments

                # Report paragraph progress
                if progress_callback:
                    progress_callback(
                        ProgressInfo(
                            chapter_num=i,
                            total_chapters=total_chapters,
                            chapter_title=chapter.get("title", ""),
                            paragraph_num=pindex + 1,
                            total_paragraphs=total_paragraphs,
                            status="paragraph",
                        )
                    )

                ptemp = str(out_path / f"pgraphs{pindex}.flac")
                if os.path.isfile(ptemp):
                    logger.debug("%s exists, skipping to next paragraph", ptemp)
                else:
                    processed_paragraph = paragraph
                    if pronunciation_processor:
                        processed_paragraph = pronunciation_processor.process_text(paragraph)

                    if multi_voice_processor:
                        voice_text_pairs = multi_voice_processor.process_paragraph(
                            processed_paragraph
                        )
                        sentences = [text for _, text in voice_text_pairs]
                        speakers = [voice for voice, _ in voice_text_pairs]
                    else:
                        sentences = sent_tokenize(processed_paragraph)
                        speakers = [speaker] * len(sentences)

                    filenames = [str(out_path / f"sntnc{z + 1}.mp3") for z in range(len(sentences))]
                    asyncio.run(
                        parallel_edgespeak(
                            sentences,
                            speakers,
                            filenames,
                            rate,
                            volume,
                            max_concurrent=max_concurrent,
                            retry_count=retry_count,
                            retry_delay=retry_delay,
                        )
                    )
                    append_silence(filenames[-1], paragraphpause)

                    sorted_files = sorted(filenames, key=sort_key)
                    title_audio_path = str(out_path / "sntnc0.mp3")
                    if os.path.exists(title_audio_path):
                        sorted_files.insert(0, title_audio_path)
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

        # Report chapter completion
        if progress_callback:
            progress_callback(
                ProgressInfo(
                    chapter_num=i,
                    total_chapters=total_chapters,
                    chapter_title=chapter.get("title", ""),
                    paragraph_num=total_paragraphs,
                    total_paragraphs=total_paragraphs,
                    status="chapter_done",
                )
            )
    return segments


def make_m4b(
    files: list[str],
    sourcefile: str,
    speaker: str,
    normalizer=None,
    silence_detector=None,
    output_dir: str | None = None,
) -> str:
    """Create M4B audiobook from chapter files.

    Args:
        files: List of FLAC chapter files
        sourcefile: Source text file path
        speaker: Speaker voice ID
        normalizer: Optional AudioNormalizer instance for volume normalization
        silence_detector: Optional SilenceDetector instance for trimming silence
        output_dir: Optional directory for output M4B file. If None, uses sourcefile directory.

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

    # Determine output paths
    basefile = os.path.basename(sourcefile).replace(".txt", "")
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        outputm4a = str(out_path / f"{basefile} ({speaker}).m4a")
        outputm4b = str(out_path / f"{basefile} ({speaker}).m4b")
        filelist = str(out_path / "filelist.txt")
        metadata_file = str(out_path / "FFMETADATAFILE")
    else:
        basefile_with_dir = sourcefile.replace(".txt", "")
        outputm4a = f"{basefile_with_dir} ({speaker}).m4a"
        outputm4b = f"{basefile_with_dir} ({speaker}).m4b"
        filelist = "filelist.txt"
        metadata_file = "FFMETADATAFILE"

    with open(filelist, "w", encoding="utf-8") as f:
        for filename in files_to_use:
            # Escape single quotes for ffmpeg
            filename = filename.replace("'", "'\\''")
            f.write(f"file '{filename}'\n")

    # Concatenate audio files
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
    subprocess.run(ffmpeg_command, check=True)

    # Add metadata and convert to AAC
    ffmpeg_command = [
        "ffmpeg",
        "-i",
        outputm4a,
        "-i",
        metadata_file,
        "-map_metadata",
        "1",
        "-codec",
        "aac",
        outputm4b,
    ]
    subprocess.run(ffmpeg_command, check=True)

    # Cleanup
    os.remove(filelist)
    os.remove(metadata_file)
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
