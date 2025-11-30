from setuptools import find_packages, setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="audiobookify",
    description="Convert EPUB files to audiobooks with enhanced chapter detection",
    author="Christopher Aedo aedo.dev",
    author_email="c@aedo.dev",
    url="https://github.com/loganrooks/audiobookify",
    license="GPL 3.0",
    version="2.3.0",
    packages=find_packages(),
    install_requires=requirements,
    extras_require={
        'tui': ['textual>=0.40.0'],
    },
    entry_points={
        'console_scripts': [
            'audiobookify = epub2tts_edge:main',
            'abfy = epub2tts_edge:main',
            'audiobookify-tui = epub2tts_edge:tui_main',
            'abfy-tui = epub2tts_edge:tui_main',
        ]
    },
)
