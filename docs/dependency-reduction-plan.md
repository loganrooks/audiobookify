# Dependency Reduction Plan

**Companion to:** [`project-review-2026-07.md`](./project-review-2026-07.md) · [`uplift-plan.md`](./uplift-plan.md)
**Question:** can audiobookify's external dependencies be brought in-house as internal modules?
**Short answer:** yes for about half of them — but *vendoring* is the wrong mechanism for
almost all of it. The right move is **reimplement or substitute**, not copy-in.

---

## Why "vendor everything" is the wrong frame

Vendoring — copying a library's source into `epub2tts_edge/_vendor/` and rewriting its
imports — is a real technique (pip itself does this). But it optimises for the wrong thing
here. It gives you *version control* over a dependency while giving you **all of its code**
to maintain, including the 95% you don't use, plus its CVEs, plus its own transitive
dependencies.

Two dependencies make this concrete:

- **nltk is 154,055 lines.** Audiobookify uses exactly one function from it: `sent_tokenize`.
  Vendoring nltk means owning 154K lines to get one function. Reimplementing that function
  means owning perhaps 150.
- **lxml and pillow ship compiled C extensions** (7 and 8 `.so` files). They cannot be
  meaningfully vendored at all without shipping a build toolchain and the libxml2/libjpeg
  system libraries with it.

So the useful question isn't "vendor or not." It's a per-dependency choice between five
strategies:

| Strategy | When it's right |
|----------|-----------------|
| **Delete** | The dependency isn't actually used |
| **Reimplement** | Narrow surface, well-understood problem, small internal module |
| **Substitute** | Something we *already* depend on can do the job (here: ffmpeg) |
| **Isolate** | Can't remove it, but can contain it behind an adapter so it's swappable |
| **Keep** | Deep surface, hard problem, or a C extension |

## The measurement

Every number below was measured against the installed environment, not estimated.

| Dependency | LOC | C ext | License | What we actually use | Verdict |
|------------|----:|:-----:|---------|----------------------|---------|
| `nltk` | 154,055 | — | Apache-2.0 | `sent_tokenize` + punkt download | 🟢 **Reimplement** |
| `textual` | 82,461 | — | MIT | 42 import sites — the whole TUI | 🔵 Keep (make optional) |
| `pillow` | 34,908 | 8 | MIT-CMU | `Image` | 🔵 Keep |
| `mutagen` | 20,061 | — | GPL-2.0 | `mp4.MP4`, `mp4.MP4Cover` | 🟢 **Substitute → ffmpeg** |
| `beautifulsoup4` | 10,634 | — | MIT | `BeautifulSoup`, `Tag` | 🔵 Keep |
| `lxml` | 8,580 | 7 | BSD-3 | `etree` | 🔵 Keep |
| `mobi` | 7,872 | — | — | `mobi.extract()` — one call | 🔵 Keep (already optional) |
| `tqdm` | 4,507 | — | MPL-2.0/MIT | `tqdm()` — one call | 🟢 **Reimplement** |
| `pydub` | 3,344 | — | MIT | 7 calls, all ffmpeg-backed | 🟢 **Substitute → ffmpeg** |
| `EbookLib` | 2,706 | — | **AGPL-3.0** | `read_epub` + 2 constants | 🟢 **Reimplement** |
| `edge-tts` | 1,420 | — | LGPL-3.0 | `Communicate` | 🟡 **Isolate, don't vendor** |
| `setuptools` | — | — | MIT | **nothing** | 🟢 **Delete** |
| `audioop-lts` | — | — | — | only because pydub needs it | 🟢 Falls out with pydub |

**Total third-party Python: ~330,500 lines. The green rows account for ~184,700 of it —
about 56%.**

---

## The four worthwhile targets

### 1. `setuptools` — delete it 🟢 *(minutes)*

`setuptools` is declared as a **runtime** dependency in `pyproject.toml` and
`requirements.txt`. Nothing in `epub2tts_edge/` imports it or `pkg_resources`. It's
vestigial — almost certainly left over from an old `pkg_resources`-based version lookup.

One line out of each file. Free.

### 2. `nltk` → an internal sentence splitter 🟢 *(1–2 weeks)*

**The single biggest win available.** 154,055 lines, and we use one function.

The cost isn't just code size. nltk's `punkt` tokenizer is a *trained model downloaded at
runtime*, which is why the project carries all of this:

- `ensure_punkt()` in `epub2tts_edge.py`, which calls `nltk.download()` on first use
- a `RUN python -c "import nltk; nltk.download(...)"` layer in the Dockerfile
- an NLTK cache step and a download step in CI
- a first-run network dependency for users who otherwise only need TTS connectivity

Replacing it removes all four, plus a 154K-line dependency, plus one more thing that can
fail behind a corporate proxy.

**The work:** a rule-based sentence splitter in `epub2tts_edge/text/sentences.py`. Split on
`.!?` followed by whitespace and a capital, with an exception list for the cases that
actually break naive splitters in prose:

- titles — `Mr. Mrs. Dr. Prof. St. Rev.`
- initials — `J. R. R. Tolkien`
- Latin — `e.g. i.e. etc. cf. et al. vs.`
- geography/orgs — `U.S. U.K. Inc. Ltd.`
- ellipses, quotes and brackets closing after terminal punctuation
- decimals and version numbers — `3.14`, `v2.5.0`

**The risk, stated plainly:** punkt is unsupervised-trained; a rule-based splitter *will*
disagree with it on edge cases. Sentences are the TTS chunking unit, so a different split
means a different audio file — different pause placement and prosody. This is a real
behavioural change, not a pure refactor.

**Mitigation:** build a golden corpus first. Run the current punkt tokenizer over a few
thousand paragraphs of representative prose, save the output, and make the new splitter's
test suite assert against it. Where they differ, judge each case on merit — several will be
punkt getting it wrong. Ship behind `--sentence-splitter {internal,nltk}` for one release
with nltk as an opt-in extra, then drop it.

### 3. `pydub` + `mutagen` → direct ffmpeg 🟢 *(1–2 weeks, do with M3)*

These two go together because they resolve to the same substitution.

**pydub is unmaintained.** Latest release `0.25.1`, uploaded **2021-03-10** — over five
years ago. It imports `audioop`, which was **removed from the Python standard library in
3.13**, which is the sole reason `audioop-lts` appears in the dependency list. That is a
dependency carried to patch a dead dependency. It will keep costing you as Python moves.

pydub is a thin ffmpeg wrapper, and audiobookify **already shells out to ffmpeg directly**
in `make_m4b()`. The whole pydub surface is seven operations:

| pydub | ffmpeg equivalent |
|-------|-------------------|
| `AudioSegment.from_file` / `.export` | `ffmpeg -i in out` |
| `AudioSegment.silent` | `-f lavfi -i anullsrc` |
| concatenation (`+`) | `-f concat` — *already used in `make_m4b()`* |
| `.dBFS` / `.max_dBFS` | `ffmpeg -af volumedetect` or `ebur128` |
| `detect_silence` | `-af silencedetect` |

Similarly, `mutagen` is used for exactly two things — opening an M4B and writing a `covr`
atom. ffmpeg embeds cover art natively with `-disposition:v attached_pic`, so this becomes
a flag on a call that already exists rather than a 20,061-line dependency.

**The work:** an `epub2tts_edge/audio/ffmpeg.py` module wrapping the ffmpeg CLI with typed
functions and proper error handling, then migrating `audio_generator.py`,
`audio_normalization.py`, and `silence_detection.py` onto it.

**Do this at the same time as the M3 performance work.** The review found that `make_m4b()`
transcodes the entire audiobook twice, and that an event loop and thread pool are created
per paragraph. Both fixes live in exactly the code this migration touches — doing them
separately means paying the same testing cost twice. Combined, this is one focused piece of
work that removes two dependencies, deletes `audioop-lts`, and roughly halves conversion
time.

**Prerequisite:** M2's coverage work. `audio_generator.py` sits at **68.61%**, better than
an earlier review pass suggested (that 22% figure was measured without ffmpeg, which skips
the tests exercising this module). But the remaining gaps sit in exactly the code this
migration touches — `make_m4b()`'s error handling and the `run_edgespeak()` retry paths.
Close those first, or you risk shipping an audiobook that goes silent from chapter 7 on.

**Partly verified already.** ffmpeg's `attached_pic` path was tested directly:

```
ffmpeg -i out.m4b -i cover.png -map 0:a -map 1:v -c:a copy -c:v mjpeg \
       -disposition:v attached_pic withcover.m4b
→ covr atom present: True | bytes: 386 | format: JPEG
```

The atom mutagen would write is the atom ffmpeg produces, read back with mutagen
itself. What remains is confirming real players display it — M4B cover art is an
area where spec and practice diverge. See [`handoff.md`](./handoff.md).

### 4. `EbookLib` → internal EPUB reader 🟢 *(1–2 weeks)*

Two independent reasons, either sufficient on its own.

**Licensing.** EbookLib is **AGPL-3.0-or-later**; audiobookify is GPL-3.0. Depending on
AGPL code is one thing — GPLv3 §13 explicitly permits the combination. *Copying AGPL source
into a GPL-3.0 codebase* is a materially murkier situation, and the AGPL's network-use
clause is not something to inherit by accident. This is precisely the case where vendoring
is the wrong tool and reimplementation is the clean one. **I'm flagging the licensing
facts, not giving legal advice — confirm before acting on it.**

**Surface.** We use `epub.read_epub()` and two constants (`ITEM_DOCUMENT`,
`ITEM_NAVIGATION`). An EPUB is a ZIP containing `META-INF/container.xml`, an OPF manifest,
and either an NCX (EPUB2) or NAV (EPUB3) table of contents. Audiobookify already parses
every one of those formats:

- `get_epub_cover()` in `epub2tts_edge.py:125` already opens the EPUB with stdlib `zipfile`
  and walks `container.xml` → OPF with `lxml.etree`
- `chapter_detector.py` already contains full NCX **and** NAV parsers — that's the
  `TOCParser` class, the project's core differentiator

So roughly 60% of the replacement is written and tested. The remaining work is spine
ordering, manifest resolution, and href normalisation. And it removes an indirection: the
detector currently reads TOC data back out of EbookLib's object model rather than from the
source it already knows how to parse.

---

## What stays, and why

**`lxml` and `pillow` — C extensions.** Not vendorable without shipping a compiler and
system libraries. Both are well-maintained with good security track records. Keep.

**`beautifulsoup4` — 10,634 lines, MIT.** Parses arbitrary real-world ebook HTML, which is
some of the most malformed markup in existence. Reimplementing a forgiving HTML parser is a
multi-year project that people have made careers out of. Keep, unreservedly.

**`textual` — 82,461 lines, MIT.** It *is* the TUI. Vendoring means becoming a TUI framework
maintainer. Keep — but make it a genuine optional extra so CLI-only users don't install it
(already M3 in the uplift plan; the review measured ~154 ms of a ~608 ms import going to an
eagerly-imported TUI).

**`mobi` — 7,872 lines.** MOBI/AZW parsing means PalmDOC and HUFF/CDIC decompression and a
fair amount of reverse-engineered Amazon format knowledge. Genuinely hard, low reward. It's
also **already a soft dependency** — `mobi_parser.py:15` wraps the import in
`try/except ImportError`. Keep, and consider moving it to an optional `[kindle]` extra so
EPUB-only users skip it.

**`edge-tts` — isolate, don't vendor.** This is the interesting one, and it deserves care.

The instinct to bring it in-house is understandable: the `<7.1.0` pin exists precisely
because an upstream release broke against Microsoft's service, and owning the client would
mean owning that. At 1,420 lines and LGPL-3.0 (which permits GPL-3.0 relicensing), it's
also the most *legally* straightforward vendoring candidate on the list.

**Don't.** The hard part of edge-tts is not the code — it's the continuously-moving DRM
token handshake, the SSL fingerprinting behaviour, and the WebSocket protocol details for
an endpoint Microsoft doesn't document and has no obligation to keep stable. Vendoring
transfers that maintenance burden onto a solo maintainer while removing the benefit of a
community that tracks the breakage collectively. You'd be taking on the worst part and
giving up the help.

The correct containment is the `TTSEngine` protocol from
[uplift M3](./uplift-plan.md#m3--break-the-single-point-of-failure-8-weeks): treat edge-tts
as *one swappable backend* behind an interface, and add a local one (Piper) that doesn't
depend on Microsoft at all. That addresses the actual risk — "Microsoft turns this off" —
which vendoring does not. Vendoring a client to a dead endpoint gets you a vendored client
to a dead endpoint.

---

## Sequencing

This work slots into the existing plan rather than competing with it.

| Step | Depends on | Effort | Removes |
|------|-----------|--------|---------|
| Delete `setuptools` | — | minutes | 1 dep |
| Reimplement `tqdm` | — | ~half a day | 4,507 LOC |
| `mobi` → optional `[kindle]` extra | — | ~half a day | 7,872 LOC from default install |
| Reimplement `EbookLib` | — | 1–2 weeks | 2,706 LOC + AGPL exposure |
| Reimplement `nltk` splitter | golden corpus | 1–2 weeks | 154,055 LOC + runtime download |
| `pydub` + `mutagen` → ffmpeg | **M2 coverage** | 1–2 weeks | 23,405 LOC + `audioop-lts` |
| `edge-tts` → `TTSEngine` protocol | — | M3 | nothing (contains risk instead) |

**Realistic total: 6–8 weeks part-time**, landing in the M2/M3 window.

**Start with `setuptools` and `tqdm`** — they're nearly free and prove the pattern.
**Do not start with pydub**, however tempting the audioop situation makes it; it's the one
item with a hard prerequisite, and doing it at 22% coverage is asking for a silent
audio-corruption bug.

### The end state

Default runtime dependencies drop from **13 to 5**:

```
beautifulsoup4   HTML parsing
lxml             XML parsing
pillow           cover image handling
edge-tts         one TTS backend among several
ffmpeg           (external binary, already required)

optional: [tui] textual   ·   [kindle] mobi
```

---

## What this actually buys you

Worth being clear-eyed, because "fewer dependencies" is not self-evidently good.

**Real gains:**
- **56% less third-party code** in the dependency tree, and with it a proportionally smaller
  CVE surface to track
- **`audioop-lts` disappears**, removing a Python-version-compatibility landmine that will
  otherwise resurface with every release
- **No runtime model download** — installs become deterministic and proxy-friendly
- **AGPL exposure removed** from a GPL-3.0 project
- **Faster, smaller installs** — meaningful for the `pipx` path the README recommends
- The pydub work **carries the M3 performance fixes along with it**, roughly halving
  conversion time

**Real costs, not to be waved away:**
- **You own the code now.** Bugs in the sentence splitter are your bugs, and they surface as
  "chapter 12 has a weird pause" rather than a stack trace.
- **Sentence splitting will change audio output.** This is the one item with genuine
  user-visible behavioural risk. The golden corpus is not optional.
- **Reimplementations start out worse than mature libraries** and only converge with real
  usage. Budget for a period where EPUB edge cases regress before they improve.
- **Effort spent here is effort not spent on features.** Given that the project's constraint
  right now is delivery rather than features, that trade is currently favourable — but it
  won't be forever.

**The honest bottom line:** the `nltk`, `pydub`/`mutagen`, and `setuptools` items are
clearly worth it — large wins with contained risk. `EbookLib` is worth it mainly for the
licensing, with the code-size saving as a bonus. `tqdm` is cosmetic. And `edge-tts`, the one
that most *feels* like it should come in-house, is the one that most clearly shouldn't.
