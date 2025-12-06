"""TTS connectivity tests.

These tests verify that edge-tts can connect to Microsoft's TTS service.
They require network access and are marked as integration tests.

Run with: pytest tests/test_tts_connectivity.py -v
"""

import asyncio
import os
import tempfile

import pytest

# Skip all tests if SKIP_TTS_TESTS env var is set
pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_TTS_TESTS", "").lower() in ("1", "true", "yes"),
    reason="TTS tests skipped via SKIP_TTS_TESTS environment variable",
)


class TestEdgeTTSConnectivity:
    """Test edge-tts connectivity to Microsoft's TTS service."""

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_edge_tts_basic_connection(self):
        """Verify edge-tts can connect and generate audio."""
        import edge_tts

        communicate = edge_tts.Communicate(
            "Hello world, this is a connectivity test.",
            "en-US-AndrewNeural",
        )

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            output_file = f.name

        try:
            await communicate.save(output_file)
            size = os.path.getsize(output_file)

            # Should generate some audio data
            assert size > 0, "Generated file should not be empty"
            assert size > 1000, f"Generated file seems too small: {size} bytes"

        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_edge_tts_with_rate(self):
        """Verify edge-tts works with rate adjustment."""
        import edge_tts

        communicate = edge_tts.Communicate(
            "Testing speech rate adjustment.",
            "en-US-AndrewNeural",
            rate="+20%",
        )

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            output_file = f.name

        try:
            await communicate.save(output_file)
            size = os.path.getsize(output_file)
            assert size > 0, "Generated file should not be empty"

        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_edge_tts_voice_list(self):
        """Verify edge-tts can list available voices."""
        import edge_tts

        voices = await edge_tts.list_voices()

        assert len(voices) > 0, "Should have available voices"

        # Check for common voice
        voice_names = [v["ShortName"] for v in voices]
        assert "en-US-AndrewNeural" in voice_names, "Should have en-US-AndrewNeural voice"


class TestEdgeTTSParallel:
    """Test parallel TTS execution."""

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_edge_tts_parallel_execution(self):
        """Verify edge-tts can handle multiple parallel requests."""
        import edge_tts

        texts = [
            "First sentence for parallel test.",
            "Second sentence for parallel test.",
            "Third sentence for parallel test.",
        ]

        output_files = []
        for _ in range(len(texts)):
            f = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            output_files.append(f.name)
            f.close()

        async def generate_audio(text: str, output: str):
            communicate = edge_tts.Communicate(text, "en-US-AndrewNeural")
            await communicate.save(output)

        try:
            # Run all 3 in parallel
            await asyncio.gather(
                *[
                    generate_audio(text, output)
                    for text, output in zip(texts, output_files, strict=True)
                ]
            )

            # Verify all generated successfully
            for output_file in output_files:
                size = os.path.getsize(output_file)
                assert size > 0, f"Generated file {output_file} should not be empty"

        finally:
            for output_file in output_files:
                if os.path.exists(output_file):
                    os.remove(output_file)


class TestEdgeTTSVersion:
    """Test edge-tts version compatibility."""

    def test_edge_tts_version_check(self):
        """Verify edge-tts version is in compatible range."""
        import edge_tts

        version = edge_tts.__version__
        parts = version.split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0

        # Version should be >= 6.1.0 and < 7.1.0 (to avoid SSL fingerprinting issues)
        assert major >= 6, f"edge-tts version {version} is too old (need >= 6.1.0)"

        if major == 7:
            assert minor < 1, (
                f"edge-tts version {version} has SSL fingerprinting issues. "
                "Downgrade to 7.0.x: pip install 'edge-tts>=6.1.0,<7.1.0'"
            )


def run_quick_tts_test():
    """Quick standalone test function for manual verification.

    Run with: python -c "from tests.test_tts_connectivity import run_quick_tts_test; run_quick_tts_test()"
    """
    import edge_tts

    print(f"edge-tts version: {edge_tts.__version__}")

    async def test():
        print("Testing TTS connectivity...")
        communicate = edge_tts.Communicate("Hello world", "en-US-AndrewNeural")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            output_file = f.name
        try:
            await communicate.save(output_file)
            size = os.path.getsize(output_file)
            print(f"SUCCESS: Generated {size} bytes")
            return True
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")
            return False
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

    return asyncio.run(test())


if __name__ == "__main__":
    run_quick_tts_test()
