# EPUB Formatting Analysis Report

This report details the formatting patterns observed in various EPUB files, focusing on elements relevant to RAG processing such as titles, chapters, sections, tables of contents, footnotes, endnotes, citations, and bibliographies.

## 1. Immanuel Kant - Critique of Pure Reason

**Source Directory:** [`test_data/real_epubs/critique_pure_reason/`](test_data/real_epubs/critique_pure_reason/)

**Date Analyzed:** 2025-05-08

**Key Files Examined:**
*   [`content.opf`](test_data/real_epubs/critique_pure_reason/content.opf)
*   [`toc.ncx`](test_data/real_epubs/critique_pure_reason/toc.ncx) (content provided by user)
*   [`text/part0012.html`](test_data/real_epubs/critique_pure_reason/text/part0012.html) (HTML ToC, content provided by user)
*   [`text/part0020.html`](test_data/real_epubs/critique_pure_reason/text/part0020.html) (Introduction, content provided by user)
*   [`text/part0023.html`](test_data/real_epubs/critique_pure_reason/text/part0023.html) (Main content example)

**Overall Structure:**
*   Highly segmented content, with numerous `partXXXX.html` and `partXXXX_split_YYY.html` files in a `text/` subdirectory.
*   Uses Calibre-specific metadata and file structures (e.g., `calibre_bookmarks.txt`).
*   Images stored with `.unknown` extension, possibly embedded fonts or special symbols.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Main Section Headers (in content files):** Typically `<h2>` (e.g., `<h2 class="h" id="calibre_pb_0">...</h2>`). Often include edition markers like `[A 19/B 33]` directly in the header text.
    *   **Sub-Section Headers:** Typically `<h3>` (e.g., `<h3 class="h1" id="sec111">...</h3>`).
    *   **HTML ToC Title:** `<h2>` with a nested `<small>` tag.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Deeply nested (depth 4). `navPoint` elements link to HTML files and specific internal anchors (e.g., `<content src="text/part0009_split_001.html#head1"/>`).
    *   **HTML ToC (e.g., `text/part0012.html`):** Present as a separate HTML file. Structured using `<p>` tags with classes like `toc`, `tocb`, `tocc` for hierarchical indentation. The OPF guide also points to `text/part0006.html` as a "Table Contents".

3.  **Footnotes/Endnotes:**
    *   **Reference Markup (in main text):** `<sup>` tags containing `<a>` tags.
        *   *Same-file notes (Author/Translator):* `<sup class="calibre18"><em class="calibre1"><a id="Fpart1fn1" href="part0023.html#Fpart1fr1" class="calibre9">1</a></em></sup>`
        *   *Different-file notes (Editorial/Glossary):* `<sup class="calibre18"><a id="ghi1" href="part0060.html#ihg1" class="calibre9">1</a></sup>`
    *   **Note Text Location:**
        *   *Author/Translator Notes:* Usually at the bottom of the *same HTML file* as the reference, within `<p class="footnotes">` elements. Each note has a target anchor `id` (e.g., `id="Fpart1fr1"`).
        *   *Editorial/Glossary Notes:* Link to a *separate HTML file* (e.g., `part0060.html`), which likely serves as a dedicated notes or glossary section.
    *   **Kant's Own Footnotes (within quoted text):** Appear within `<div class="quote">` blocks, using the same `<sup><a>...</a></sup>` pattern, linking to note text at the bottom of the same file.

4.  **Citations/References (within note text):**
    *   Observed as plain text within the footnote paragraphs (e.g., `(EX, p. 15; 23:21)` for references to Kant's personal copy annotations).

5.  **Bibliography:**
    *   Not explicitly identified as a separate "Bibliography" section yet. Editorial notes in `part0060.html` might contain or lead to bibliographic information.

6.  **Page Number Markers:**
    *   Embedded in text using `<a id="page_XXX" class="calibre10"></a>`.

7.  **Edition Markers (e.g., A/B pagination for Kant):**
    *   Appear as plain text directly within or near headings (e.g., `[A 19/B 33]`).

8.  **Images:**
    *   Stored in an `images/` directory with `.unknown` extensions. Referenced in HTML via `<img>` tags. Likely used for special symbols or characters not easily represented by standard text/fonts. Media type in OPF is `application/octet-stream`.

**Summary for "Critique of Pure Reason":**
This EPUB demonstrates a complex, scholarly formatting style. Key challenges for RAG include:
*   Distinguishing between authorial footnotes (same-file) and editorial/glossary endnotes (different-file).
*   Correctly associating edition markers (A/B numbers) with the text they refer to.
*   Handling the highly segmented nature of content files (`_split_` files).
*   Interpreting the purpose of `.unknown` image files.
*   The presence of an HTML ToC in addition to the NCX ToC.

---
## 2. Charles Taylor - Hegel

**Source Directory:** [`test_data/real_epubs/hegel_charles_taylor/`](test_data/real_epubs/hegel_charles_taylor/)

**Date Analyzed:** 2025-05-08

**Key Files Examined:**
*   [`content.opf`](test_data/real_epubs/hegel_charles_taylor/content.opf)
*   [`toc.ncx`](test_data/real_epubs/hegel_charles_taylor/toc.ncx)
*   [`text/part0009.html`](test_data/real_epubs/hegel_charles_taylor/text/part0009.html) (Chapter I example)

**Overall Structure:**
*   Content segmented into `partXXXX.html` files within a `text/` directory. No evidence of automatic file splitting (like `_split_` suffixes).
*   Uses standard image formats (`.jpeg`) in an `images/` directory.
*   Includes Calibre metadata.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Chapter Number:** `<h3>` with class `h1` and nested `<span>` (e.g., `<span class="small">CHAPTER I</span>`).
    *   **Chapter Title:** `<h3>` with class `h3a` and nested `<em>`.
    *   **Numbered Sub-sections:** `<h4>` or `<p>` with class `center-num`.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Depth 4. Links to HTML files and internal anchors (e.g., `text/part0020.html#sec1`). Uses `class="chapter"` for all `navPoint` elements.
    *   **HTML ToC (`text/part0004.html`):** Referenced in OPF guide section. (Content not examined in detail).

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses footnotes (note text at the end of the same HTML file).
    *   **Reference Markup:** `<sup class="calibre20"><a id="pX-fnY" href="partZZZZ.html#pXfnY">Y</a></sup>`.
    *   **Note Text Location:** At the bottom of the corresponding HTML file, using `<p class="footnote">`. Each note begins with a matching superscripted anchor: `<sup class="calibre22"><a id="pXfnY" href="partZZZZ.html#pX-fnY">Y</a></sup>`.

4.  **Citations/References (within note text):**
    *   Book/article titles typically italicized using `<em class="calibre8">`. Other publication details are plain text within the `<p class="footnote">`.

5.  **Bibliography:**
    *   Explicitly referenced in NCX, linking to a dedicated file: [`text/part0035.html`](test_data/real_epubs/hegel_charles_taylor/text/part0035.html). (Content not examined in detail).

6.  **Index:**
    *   Explicitly referenced in NCX, linking to a dedicated file: [`text/part0037.html`](test_data/real_epubs/hegel_charles_taylor/text/part0037.html). (Content not examined in detail).

7.  **Page Number Markers:**
    *   Embedded using `<a id="page_X" class="calibre3"></a>`.

8.  **Poetry Formatting:**
    *   Uses multiple `<p class="tocc">` tags, often with nested `<span>` tags for indentation.

**Summary for "Hegel" by Charles Taylor:**
This EPUB presents a well-structured academic format. Key features include same-page footnotes, a multi-level NCX ToC complemented by an HTML ToC, and dedicated sections for Bibliography and Index. Identifying header levels relies on specific tag/class combinations.
## 3. Hegel - Science of Logic

**Source Directory:** [`test_data/real_epubs/hegel_science_of_logic/`](test_data/real_epubs/hegel_science_of_logic/)

**Date Analyzed:** 2025-05-08

**Key Files Examined:**
*   [`content.opf`](test_data/real_epubs/hegel_science_of_logic/content.opf)
*   [`toc.ncx`](test_data/real_epubs/hegel_science_of_logic/toc.ncx)
*   [`Georg_Wilhel-ience_of_Logic_split_013.html`](test_data/real_epubs/hegel_science_of_logic/Georg_Wilhel-ience_of_Logic_split_013.html) (Introduction title page)
*   [`Georg_Wilhel-ience_of_Logic_split_014.html`](test_data/real_epubs/hegel_science_of_logic/Georg_Wilhel-ience_of_Logic_split_014.html) (Introduction content)

**Overall Structure:**
*   Content is heavily segmented into numerous `_split_XXX.html` files located directly in the root EPUB directory (not a `text/` subfolder).
*   Contains a very large number of `.jpg` images, some used for rendering special text (e.g., Greek words).
*   Includes Calibre metadata.
*   A `toc.ncx` file is present and used for primary navigation.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Major Section Titles (e.g., "Introduction"):** Often appear on their own minimal HTML page, using `<h1>` (e.g., `<h1 id="filepos328133" class="calibre39">...</h1>`).
    *   **Sub-Section Headers (e.g., "General concept of logic"):** `<h2>` (e.g., `<h2 class="calibre41" id="calibre_pb_25">...</h2>`).
    *   Headers may contain `<span>` elements with page/section markers (e.g., `<span class="calibre40">21.27</span>`).

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Depth 2 (relatively flat). Links to the split HTML files, often with `#fileposXXXXX` anchors.
    *   **HTML ToC (`Georg_Wilhel-ience_of_Logic_split_005.html`):** Referenced in OPF guide section. (Content not examined in detail).

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses footnotes (note text at the end of the same HTML file where the reference occurs).
    *   **Reference Markup:** `<span><a id="fileposXXXXX">...</a><a href="#fileposYYYYY"><sup class="calibre30">N</sup></a></span>`. The first `<a>` tag often contains an empty `<span>` with an underline class.
    *   **Note Text Location:** At the bottom of the corresponding HTML file. Each note is typically structured as: `<div class="calibre32" id="fileposYYYYY"><div class="calibre33"><blockquote class="calibre14"><span><a href="#fileposXXXXX">...</a></sup></span> ...note text... </blockquote></div></div>`.

4.  **Citations/References (within note text):**
    *   Book/article titles typically italicized using `<span><span class="italic1">...</span></span>`. Other publication details are plain text.

5.  **Bibliography:**
    *   Explicitly referenced in NCX, linking to [`Georg_Wilhel-ience_of_Logic_split_056.html`](test_data/real_epubs/hegel_science_of_logic/Georg_Wilhel-ience_of_Logic_split_056.html). (Content not examined in detail).

6.  **Index:**
    *   Explicitly referenced in NCX, linking to [`Georg_Wilhel-ience_of_Logic_split_057.html`](test_data/real_epubs/hegel_science_of_logic/Georg_Wilhel-ience_of_Logic_split_057.html). (Content not examined in detail).

7.  **Page/Section Markers (e.g., `21.28`, `21.44`):**
    *   Appear within `<span class="calibre37">` tags, usually at the end of paragraphs or near anchors.

8.  **Images for Special Text:**
    *   Used for non-standard characters or words (e.g., Greek text rendered as an image: `<img alt="" src="images/00003.jpg" class="calibre18"/>`).

**Summary for "Hegel's Science of Logic":**
This EPUB is characterized by its extensive file splitting and heavy use of images for text elements. Footnotes are same-page but use a specific nested div/blockquote structure. The NCX ToC is flatter than in other complex philosophical works examined. The reliance on `fileposXXXXX` anchors is prominent.
## 4. Hegel - Elements of the Philosophy of Right

**Source Directory:** [`test_data/real_epubs/hegels_elements_of_the_philosophy_of_right/`](test_data/real_epubs/hegels_elements_of_the_philosophy_of_right/)

**Date Analyzed:** 2025-05-08

**Key Files Examined:**
*   [`content.opf`](test_data/real_epubs/hegels_elements_of_the_philosophy_of_right/content.opf)
*   [`toc.ncx`](test_data/real_epubs/hegels_elements_of_the_philosophy_of_right/toc.ncx)
*   [`text/part0009.html`](test_data/real_epubs/hegels_elements_of_the_philosophy_of_right/text/part0009.html) (Main title page)
*   [`text/part0010.html`](test_data/real_epubs/hegels_elements_of_the_philosophy_of_right/text/part0010.html) (HTML Table of Contents)
*   [`text/part0011.html`](test_data/real_epubs/hegels_elements_of_the_philosophy_of_right/text/part0011.html) (Preface content)

**Overall Structure:**
*   Content segmented into `partXXXX.html` files, with some evidence of `_split_` files (e.g., `part0002_split_XXX.html`).
*   Includes embedded `.ttf` font files, with `encryption.xml` present, suggesting font obfuscation.
*   Standard Calibre metadata and structure.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX). The main work's title page ([`text/part0009.html`](test_data/real_epubs/hegels_elements_of_the_philosophy_of_right/text/part0009.html)) uses `<p class="centerhead2">`.
    *   **Section Headers (e.g., "Preface"):** `<h2>` with class `h1`.
    *   **HTML ToC Title:** `<h2>` with class `h2b`.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Depth 2. Links to HTML files and anchors (e.g., `#ele`).
    *   **HTML ToC (`text/part0010.html`):** Very detailed, multi-level ToC using various `<p>` classes (`toc`, `toc2a`, `toc-part`, `toc-front`, `toc1`, `toc2`, `toc3a`, etc.) for hierarchical structure and indentation.

3.  **Footnotes/Endnotes:**
    *   **Dual System:**
        *   **Endnotes (Editor/Translator):** Numbered references like `<sup class="calibre11"><a id="ipreenX" href="part0029.html#preenX"><em class="calibre3">N</em></a></sup>`. These link to a separate HTML file ([`part0029.html`](test_data/real_epubs/hegels_elements_of_the_philosophy_of_right/text/part0029.html)) which presumably contains the collected endnotes.
        *   **Footnotes (Author's/Hegel's):** Marked with symbols (e.g., `†`, `*`) like `<sup class="calibre11"><a id="ifnX" href="part0011.html#fnX"><em class="calibre3">†</em></a></sup>`. The note text appears at the bottom of the *same HTML file* as the reference, within `<p class="footnote">`.
    *   This distinction between note types and their locations is a key feature.

4.  **Citations/References (within note text):**
    *   (Detailed analysis would require examining `part0029.html` and footnote sections of content files).

5.  **Bibliography:**
    *   Explicitly referenced in NCX ("Select bibliography"), linking to [`text/part0032.html`](test_data/real_epubs/hegels_elements_of_the_philosophy_of_right/text/part0032.html).

6.  **Index:**
    *   Explicitly referenced in NCX ("Index of subjects", "Index of names"), linking to [`text/part0033.html`](test_data/real_epubs/hegels_elements_of_the_philosophy_of_right/text/part0033.html) and [`text/part0034.html`](test_data/real_epubs/hegels_elements_of_the_philosophy_of_right/text/part0034.html).

7.  **Page Number Markers:**
    *   Embedded using `<a id="page_X" class="calibre9"></a>`.

8.  **Poetry Formatting:**
    *   Uses `<div class="poem">` with `<p class="poemline">`. Greek text within poetry is rendered using `<span>` tags with class `normal`.

9.  **Embedded Fonts:**
    *   `.ttf` font files are listed in the OPF manifest (e.g., `<item href="fonts/00001.ttf" ... media-type="application/x-font-truetype"/>`).
    *   The presence of `META-INF/encryption.xml` strongly suggests these fonts are obfuscated/encrypted according to EPUB specifications.

**Summary for "Hegel's Elements of the Philosophy of Right":**
This EPUB is significant for its dual footnote/endnote system and its use of embedded (likely obfuscated) fonts. The HTML ToC is highly structured. These features provide excellent test cases for handling diverse annotation styles and font dependencies.
## 5. Robert B. Pippin - Hegel’s Realm of Shadows

**Source Directory:** [`test_data/real_epubs/hegels_realm_of_shadows/`](test_data/real_epubs/hegels_realm_of_shadows/)

**Date Analyzed:** 2025-05-08

**Key Files Examined:**
*   [`OEBPS/content.opf`](test_data/real_epubs/hegels_realm_of_shadows/OEBPS/content.opf)
*   [`OEBPS/toc.xhtml`](test_data/real_epubs/hegels_realm_of_shadows/OEBPS/toc.xhtml) (EPUB 3 Navigation Document)
*   [`OEBPS/chi-pippin-hegels-0008.xhtml`](test_data/real_epubs/hegels_realm_of_shadows/OEBPS/chi-pippin-hegels-0008.xhtml) (Chapter 1 example)

**Overall Structure:**
*   EPUB 3 format.
*   Content files and resources are located within an `OEBPS/` directory.
*   Uses an EPUB 3 Navigation Document (`toc.xhtml`) with `properties="nav"`.
*   Includes a `toc.ncx` for backward compatibility.
*   No embedded fonts declared in the OPF manifest.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) with main and subtitle distinguished by `<meta property="title-type">`.
    *   **Chapter Number:** `<h1>` with class `cn`.
    *   **Chapter Title:** `<h1>` with class `ct`.
    *   **Sub-headers:** `<h2>` with class `ah`.

2.  **Table of Contents (ToC):**
    *   **EPUB 3 Nav Doc (`toc.xhtml`):** Primary navigation. Uses nested `<ol>` and `<li>` for hierarchy. Contains `epub:type` attributes for landmarks (cover, toc, bodymatter, copyright-page) and a page-list.
    *   **HTML ToC (Formatted):** A separate [`chi-pippin-hegels-0005.xhtml`](test_data/real_epubs/hegels_realm_of_shadows/OEBPS/chi-pippin-hegels-0005.xhtml) is linked from the Nav Doc as the human-readable "CONTENTS" page.
    *   **NCX ToC (`toc.ncx`):** Present for EPUB 2 compatibility.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses endnotes.
    *   **Reference Markup (in main text):** `<a class="fnref" href="[target_notes_file.xhtml]#fnX" id="fnXr">N</a>`.
    *   **Note Text Location:** All endnotes are collected in a dedicated HTML file ([`chi-pippin-hegels-0020.xhtml`](test_data/real_epubs/hegels_realm_of_shadows/OEBPS/chi-pippin-hegels-0020.xhtml)), as indicated by an explicit "Footnotes" link in the `toc.xhtml`. (Internal structure of the notes file itself would require further examination).

4.  **Citations/References (within note text):**
    *   (To be confirmed by examining `chi-pippin-hegels-0020.xhtml`).

5.  **Bibliography/Reference List:**
    *   Explicitly referenced in `toc.xhtml`, linking to [`chi-pippin-hegels-0018.xhtml`](test_data/real_epubs/hegels_realm_of_shadows/OEBPS/chi-pippin-hegels-0018.xhtml).

6.  **Index:**
    *   Explicitly referenced in `toc.xhtml`, linking to [`chi-pippin-hegels-0019.xhtml`](test_data/real_epubs/hegels_realm_of_shadows/OEBPS/chi-pippin-hegels-0019.xhtml).

7.  **Page Number Markers:**
    *   Embedded using `<a class="page" id="pX"/>` or `<a class="page" data-locator="pX"/>`.

8.  **Epigraphs:**
    *   Formatted using `<div class="epigraph">` containing `<p class="epf">`.

9.  **Cross-References (internal):**
    *   Links to other parts of the book use `<a class="xref" href="...">...</a>`.

**Summary for "Hegel's Realm of Shadows":**
This EPUB 3 example showcases a clean structure with endnotes consolidated into a separate file, which is beneficial for targeted RAG processing. The use of `epub:type` in the navigation document provides good semantic clues. The lack of embedded fonts simplifies one aspect of processing.
## 6. Martin Heidegger - German Existentialism

**Source Directory:** [`test_data/real_epubs/heidegger_german_existentialism/`](test_data/real_epubs/heidegger_german_existentialism/)

**Date Analyzed:** 2025-05-08

**Key Files Examined:**
*   [`OEBPS/e9780806536255_content.opf`](test_data/real_epubs/heidegger_german_existentialism/OEBPS/e9780806536255_content.opf)
*   [`OEBPS/toc.ncx`](test_data/real_epubs/heidegger_german_existentialism/OEBPS/toc.ncx)
*   [`OEBPS/e9780806536255_c01.html`](test_data/real_epubs/heidegger_german_existentialism/OEBPS/e9780806536255_c01.html) (Content example)

**Overall Structure:**
*   EPUB 2 format.
*   Content files and resources are located within an `OEBPS/` directory.
*   Filenames are prefixed (e.g., `e9780806536255_`).
*   A dedicated HTML file for notes (`e9780806536255_ftn01.html`) is present and included in the spine.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Section Titles:** Typically within a `<div class="title-chapter">`, often using `<span class="b">` for bold text.
    *   **Subtitles:** Typically within a `<div class="subtitle-chapter">`, often using `<span class="i">` for italic text.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Depth 2. Links to the various HTML content files.
    *   **HTML ToC (`e9780806536255_toc01.html`):** Referenced in OPF guide. (Structure not detailed here but assumed to be a standard HTML list).

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses endnotes.
    *   **Reference Markup (in main text):** `<sup><a href="e9780806536255_ftn01.html#ftn_fnX" id="ref_ftn_fnX"><span><span class="footnote_number">N</span></span></a></sup>`.
    *   **Note Text Location:** All endnotes are collected in the dedicated HTML file [`e9780806536255_ftn01.html`](test_data/real_epubs/heidegger_german_existentialism/OEBPS/e9780806536255_ftn01.html), as indicated by the OPF manifest, spine, and NCX. (Internal structure of this notes file would require separate examination).

4.  **Paragraphs:**
    *   Commonly structured as `<div class="p-indent"><span>...text...</span></div>`.

5.  **Emphasis:**
    *   Italics: `<span class="i">...</span>`.
    *   Bold: `<span class="b">...</span>`.

6.  **Embedded Fonts:**
    *   No embedded fonts are declared in the OPF manifest.

**Summary for "German Existentialism":**
This EPUB uses a div-based structure for paragraphs and relies on classes for styling emphasis. A key feature is the consolidation of all notes into a single endnotes file (`_ftn01.html`), making them centrally accessible. The NCX provides a flat navigation for the main articles/sections.
## 7. Heidegger - The Metaphysics of German Idealism

**Source Directory:** [`test_data/real_epubs/heidegger_the_metaphysics_of_german_idealism/`](test_data/real_epubs/heidegger_the_metaphysics_of_german_idealism/)

**Date Analyzed:** 2025-05-08

**Key Files Examined:**
*   [`OPS/content.opf`](test_data/real_epubs/heidegger_the_metaphysics_of_german_idealism/OPS/content.opf)
*   [`OPS/toc.xhtml`](test_data/real_epubs/heidegger_the_metaphysics_of_german_idealism/OPS/toc.xhtml) (EPUB 3 Navigation Document)
*   [`OPS/c01.xhtml`](test_data/real_epubs/heidegger_the_metaphysics_of_german_idealism/OPS/c01.xhtml) (Chapter 1 example)

**Overall Structure:**
*   EPUB 3 format.
*   Content files and resources are located within an `OPS/` directory.
*   Uses an EPUB 3 Navigation Document (`toc.xhtml`) with `properties="nav"`.
*   Includes a `toc.ncx` for backward compatibility.
*   Contains detailed accessibility metadata in the OPF.
*   No embedded fonts declared in the OPF manifest.
*   CSS includes a publisher template (`WileyTemplate_v5.5.css`).

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and in `toc.xhtml`.
    *   **Chapter Title/Number:** Combined in an `<h1>` tag; chapter number in `<span class="chapterNumber">`, title in `<span class="chapterTitle">`.
    *   **Section Headers (e.g., § 8):** `<h2>` tags, often using `<b>` and `<i>` for emphasis within the header text.

2.  **Table of Contents (ToC):**
    *   **EPUB 3 Nav Doc (`toc.xhtml`):** Primary navigation. Uses nested `<ol>` and `<li>` for hierarchy. Contains `epub:type` attributes for landmarks (cover, toc, bodymatter, frontmatter, backmatter) and a page-list.
    *   **NCX ToC (`toc.ncx`):** Present for EPUB 2 compatibility.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses same-page footnotes (notes appear at the end of the XHTML file where they are referenced).
    *   **Reference Markup (in main text):** `<sup><a aria-describedby="fnX" epub:type="noteref" href="#fnX" id="ftX">N</a></sup>`.
    *   **Note Text Location:** At the bottom of each content XHTML file, within a `<section class="notesSet" role="doc-endnotes">` containing an `<ol class="notesList">`. Each note is an `<li class="noteEntry" role="doc-endnote">`.
    *   Translator's notes are clearly marked with `{TN: ...}`.

4.  **Citations/References (within note text):**
    *   Book/article titles often italicized (using `<i>` or class-styled `<span>`). Other details are plain text.

5.  **Bibliography/Glossaries/Appendix:**
    *   Separate XHTML files for these (e.g., `b03.xhtml`, `b09.xhtml`) are linked from the `toc.xhtml`.

6.  **Page Number Markers:**
    *   EPUB 3 style: `<span aria-label="X" epub:type="pagebreak" id="Page_X" role="doc-pagebreak"/>`.

7.  **Emphasis:**
    *   Italics: `<i>` or class-styled `<span>`.
    *   Bold: `<b>` or class-styled `<span>`.

**Summary for "Heidegger: The Metaphysics of German Idealism":**
This EPUB 3 example uses footnotes collected at the end of each chapter's XHTML file, marked up semantically using `epub:type="noteref"` and `role="doc-endnote"`. It has a comprehensive HTML ToC with landmarks and a page list. The structure is fairly standard for a modern, professionally produced EPUB.
## 8. Marx & Engels - The Marx-Engels Reader

**Source Directory:** [`test_data/real_epubs/marx_engels_reader/`](test_data/real_epubs/marx_engels_reader/)

**Date Analyzed:** 2025-05-08

**Key Files Examined:**
*   [`content.opf`](test_data/real_epubs/marx_engels_reader/content.opf)
*   [`toc.ncx`](test_data/real_epubs/marx_engels_reader/toc.ncx)
*   [`text/part0006_split_000.html`](test_data/real_epubs/marx_engels_reader/text/part0006_split_000.html) (Introductory note to a section)
*   [`text/part0006_split_001.html`](test_data/real_epubs/marx_engels_reader/text/part0006_split_001.html) (Content example)

**Overall Structure:**
*   EPUB 2 format.
*   Content is heavily segmented into numerous `partXXXX_split_YYY.html` files within a `text/` directory, a characteristic of Calibre processing.
*   Includes Calibre metadata.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Section Titles:** Often appear in an initial `_split_000.html` file for a given section, typically using `<p>` tags with specific styling classes (e.g., `<p class="s24">`). Subsequent `_split_XXX.html` files for that section may not repeat the main header.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Depth 2. Links to the various (often split) HTML content files. "PART" divisions are listed, but individual articles/works within those parts often appear as sibling `navPoint`s rather than deeply nested children in the NCX.
    *   **HTML ToC:** No explicit HTML ToC file is referenced in the OPF `<guide>` section, though one might exist among the early `partXXXX.html` files.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses endnotes.
    *   **Reference Markup (in main text):** `<a id="footnote-refXX" href="part0057.html#footnoteXX" class="calibre8"><span><sup class="calibre9">N</sup></span></a>`.
    *   **Note Text Location:** All endnotes are collected in a dedicated HTML file, [`part0057.html`](test_data/real_epubs/marx_engels_reader/text/part0057.html), as indicated by the NCX "Footnotes" entry and the `href` attributes in the note references. (Internal structure of this notes file would require separate examination).

4.  **Citations/References (within note text):**
    *   (To be confirmed by examining `part0057.html`).

5.  **Bibliography:**
    *   A "Bibliographic Note" is linked in the NCX to [`text/part0056_split_000.html`](test_data/real_epubs/marx_engels_reader/text/part0056_split_000.html).

6.  **Emphasis:**
    *   Italics often rendered using `<span class="c1">` or `<span class="c5">`.

7.  **Poetry/Blockquotes:**
    *   Uses `<p>` tags with specific classes (e.g., `s20`, `s25` for poetry).

**Summary for "The Marx-Engels Reader":**
This EPUB is characterized by extensive file splitting due to Calibre processing. It employs an endnote system, with all notes consolidated into a single HTML file. Section headers are often found in the first split file of a section. The NCX provides a somewhat flat navigation structure for the individual readings within larger parts.
## 9. Marcuse - Marxism, Revolution and Utopia

**Source Directory:** [`test_data/real_epubs/marxism_revolution_utopia_marcuse/`](test_data/real_epubs/marxism_revolution_utopia_marcuse/)

**Date Analyzed:** 2025-05-08

**Key Files Examined:**
*   [`OEBPS/content.opf`](test_data/real_epubs/marxism_revolution_utopia_marcuse/OEBPS/content.opf)
*   [`OEBPS/toc.ncx`](test_data/real_epubs/marxism_revolution_utopia_marcuse/OEBPS/toc.ncx)
*   [`OEBPS/007_9781315814797_chapter1.html`](test_data/real_epubs/marxism_revolution_utopia_marcuse/OEBPS/007_9781315814797_chapter1.html) (Content example)

**Overall Structure:**
*   EPUB 2 format.
*   Content files and resources are located within an `OEBPS/` directory.
*   Filenames use a numerical prefix and an ISBN-like string.
*   Includes embedded `.ttf` fonts (Segoe UI, Times variants).
*   Includes figures as `.gif` images.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Part Headers:** `<h1>` with class `header`.
    *   **Part Titles:** `<h1>` with nested `<span>`.
    *   **Section/Article Titles:** `<h2>` tags.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Depth 2. Uses nested `navPoint` elements for Parts and the articles/sections within them, linking to HTML files and specific anchors (e.g., `#ch1.1`).
    *   **HTML ToC (`004_9781315814797_contents.html`):** Referenced in OPF guide.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses same-page footnotes (notes appear at the end of the XHTML file where they are referenced).
    *   **Reference Markup:** Uses two distinct styles within `<a>` tags:
        *   Asterisk marker: `*` (e.g., `<a href="#fn-fnref1_1" id="fn1_1">*</a>`) - Possibly for editorial notes.
        *   Numbered superscript marker: `<sup>N</sup>` (e.g., `<a href="#fn-fnref1_5" id="fn1_5"><sup>1</sup></a>`) - Possibly for author/source notes.
    *   **Note Text Location:** At the bottom of each content XHTML file. Uses `<p class="fn1">` for notes referenced by `*`, starting with the linked `<a>*</a>` marker. Uses `<p class="fn">` for numbered notes, starting with `<span class="label"><a>N</a></span>`.

4.  **Citations/References (within note text):**
    *   Book/article titles often italicized using `<em>`. Other details are plain text.

5.  **Bibliography:**
    *   No separate Bibliography file listed in OPF or NCX. Bibliographic information might be within notes or text.

6.  **Index:**
    *   An Index file ([`013_9781315814797_index.html`](test_data/real_epubs/marxism_revolution_utopia_marcuse/OEBPS/013_9781315814797_index.html)) is listed in the OPF and linked in the NCX.

7.  **Page Number Markers:**
    *   Embedded using `<a id="pX"/>`.

8.  **Embedded Fonts:**
    *   `.ttf` font files (Segoe UI, Times) are listed in the OPF manifest.

**Summary for "Marxism, Revolution and Utopia":**
This EPUB 2 uses same-page footnotes with two distinct reference styles (* and numbers), potentially indicating different note types. It embeds common fonts and includes figures as images. The NCX provides a clear two-level hierarchy.
## 10. Adorno - Negative Dialectics

**Source Directory:** [`test_data/real_epubs/negative_dialectics/`](test_data/real_epubs/negative_dialectics/)

**Date Analyzed:** 2025-05-08

**Key Files Examined:**
*   [`content.opf`](test_data/real_epubs/negative_dialectics/content.opf)
*   [`toc.ncx`](test_data/real_epubs/negative_dialectics/toc.ncx)
*   [`index_split_001.html`](test_data/real_epubs/negative_dialectics/index_split_001.html) (Prologue and start of Introduction)

**Overall Structure:**
*   EPUB 2 format.
*   Content files (`index_split_XXX.html`) are located directly in the root EPUB directory and are heavily segmented (likely by Calibre).
*   Includes Calibre metadata.
*   No embedded fonts or non-cover images declared in the OPF manifest.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Section Titles (e.g., "Prologue", "Introduction"):** Use `<p>` tags with specific classes and styled `<span>` elements (e.g., `<p class="calibre_1"><span class="calibre3"><span class="bold">...</span></span></p>`).
    *   **Sub-topic Headers:** Also use `<p>` tags with bolded spans, sometimes including what appear to be print page range references (e.g., "On the Possibility of Philosophy 15-16").

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Highly problematic. Many `<navLabel>` elements contain long excerpts of text from the book instead of concise titles. Links to `index_split_XXX.html` files. Does not list a separate notes, bibliography, or index section.
    *   **HTML ToC:** The OPF `<guide>` section points to [`index_split_081.html`](test_data/real_epubs/negative_dialectics/index_split_081.html) (the last content file) for the Table of Contents. (Actual structure of this HTML ToC not yet examined).

3.  **Footnotes/Endnotes:**
    *   **Type:** Uncertain, likely print-style footnotes not converted to linked EPUB notes.
    *   **Reference Markup (in main text):** Unlinked superscripted numbers (e.g., `<sup class="calibre5"><small class="calibre6"><span class="calibre7">N</span></small></sup>`). There are no `<a>` tags with `href` attributes associated with these superscripts.
    *   **Note Text Location:** Not found within the examined content file (`index_split_001.html`). Their location is unknown; they might be at the end of the book (possibly in one of the later `index_split_XXX.html` files) or may have been omitted during EPUB conversion if they were bottom-of-page print footnotes. This lack of hyperlinking is a major issue for digital navigation and RAG.

4.  **Citations/References (within note text):**
    *   (Dependent on finding the note text, if it exists in the EPUB).

5.  **Bibliography/Index:**
    *   Not explicitly identified in the NCX or the examined content file. May be part of the final split files, potentially near or within the HTML ToC in `index_split_081.html`.

6.  **Emphasis:**
    *   Italics: Often rendered using `<span class="underline">`. This is an unconventional use of a class name typically associated with underlining.
    *   Bold: `<span class="bold">`.

7.  **Page Number Markers:**
    *   Print page ranges sometimes appear in sub-topic headers. No standard EPUB page break anchors (like `<a id="page_X">` or `epub:type="pagebreak"`) observed in the examined content file.

**Summary for "Negative Dialectics":**
This EPUB presents significant challenges for automated processing due to its heavily segmented nature, a highly problematic NCX ToC, and, most critically, unlinked footnote/endnote markers. The unusual location of the HTML ToC at the very end of the book and the unconventional use of CSS classes for emphasis add further complexity. Locating and associating note text with its references will be a primary difficulty for RAG.
## 11. Derrida - Of Grammatology

**Source Directory:** [`test_data/real_epubs/of_grammatology/`](test_data/real_epubs/of_grammatology/)

**Date Analyzed:** 2025-05-08

**Key Files Examined:**
*   [`OEBPS/content.opf`](test_data/real_epubs/of_grammatology/OEBPS/content.opf)
*   [`OEBPS/toc.ncx`](test_data/real_epubs/of_grammatology/OEBPS/toc.ncx)
*   [`OEBPS/Text/ch01.html`](test_data/real_epubs/of_grammatology/OEBPS/Text/ch01.html) (Chapter 1 example)

**Overall Structure:**
*   EPUB 2 format.
*   Content files and resources are located within an `OEBPS/` directory, with text content further in an `OEBPS/Text/` subdirectory.
*   Filenames for content often use prefixes like `chXX_` or `ch00_fmXX_`.
*   A large number of small HTML files named `chXX_fnYY.html` exist, corresponding to individual footnotes.
*   Includes embedded `.ttf` fonts (Charis SIL variants).

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Chapter Title/Number:** `<h3>` with class `h3b`, using `<strong>` for number and `<em>` for title.
    *   **Section Headers:** `<h4>` with class `h4`, using `<strong>` and `<em>`.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Hierarchical, linking to HTML files and anchors. Contains a `dtb:depth` of "1" but actually has multiple levels of nesting for chapters and sections. Unusually, it includes a deeply nested section attempting to list and link to every individual footnote file (`chXX_fnYY.html`).
    *   **HTML ToC (`OEBPS/Text/ch00_fm04_toc.html`):** Referenced in OPF guide. (Structure not detailed here).

3.  **Footnotes/Endnotes:**
    *   **Dual System / Highly Granular for some notes:**
        *   **Type 1 (Symbol-marked notes):** Referenced with symbols (`*`, `†`, `§`, `||`) using `<a class="nounder" href="../Text/chXX_fnYY.html#footZZZ">*</a>`. Each of these links to a *separate, small HTML file* (e.g., `ch01_fn01.html`, `ch01_fn02.html`) that contains the text for that specific note (or a small group if a single file has multiple anchors like `foot004`, `foot005`).
        *   **Type 2 (Numbered notes):** Referenced with superscripted numbers `<sup><a class="nounder" href="../Text/ch08_notes.html#chXXenYYa">N</a></sup>`. These link to anchors within a single, consolidated endnotes file, [`OEBPS/Text/ch08_notes.html`](test_data/real_epubs/of_grammatology/OEBPS/Text/ch08_notes.html).
    *   This hybrid approach, especially the creation of individual HTML files for many symbol-marked notes, is a very distinctive and complex pattern.

4.  **Citations/References (within note text):**
    *   (To be confirmed by examining the various `chXX_fnYY.html` files and `ch08_notes.html`).

5.  **Bibliography/Index:**
    *   "Index" linked in NCX to [`OEBPS/Text/ch09_index.html`](test_data/real_epubs/of_grammatology/OEBPS/Text/ch09_index.html).
    *   No explicit "Bibliography" in NCX, but could be part of the "Notes" section or another back matter component.

6.  **Page Number Markers:**
    *   Embedded using `<a id="page_X"></a>`.

7.  **Emphasis:**
    *   Italics: `<em>`.
    *   Bold: `<strong>`.

8.  **Embedded Fonts:**
    *   Charis SIL `.ttf` fonts are listed in the OPF manifest with `media-type="application/vnd.ms-opentype"`.

**Summary for "Of Grammatology":**
This EPUB exhibits a highly complex and granular system for handling symbol-marked footnotes, creating separate small HTML files for many of them, in addition to a consolidated endnotes file for numbered notes. This will be a significant challenge for RAG to correctly resolve and associate all note content. The NCX reflects this complexity by attempting to list these individual footnote files.
## 12. Zizek, Ruda, Hamza - Reading Hegel

**Source Directory:** [`test_data/real_epubs/reading_hegel_zizek/`](test_data/real_epubs/reading_hegel_zizek/)

**Date Analyzed:** 2025-05-08

**Key Files Examined:**
*   [`content.opf`](test_data/real_epubs/reading_hegel_zizek/content.opf)
*   [`toc.ncx`](test_data/real_epubs/reading_hegel_zizek/toc.ncx)
*   [`OEBPS/part0006.xhtml`](test_data/real_epubs/reading_hegel_zizek/OEBPS/part0006.xhtml) (Chapter 1 example)

**Overall Structure:**
*   EPUB 2 format.
*   Content files (`partXXXX.xhtml`) are located within an `OEBPS/` subdirectory.
*   Includes Calibre metadata.
*   A `page-map.xml` file is present and referenced in the spine for print page navigation.
*   Relatively few content files compared to heavily split examples.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Chapter Title/Number:** Uses `<div>` elements with specific classes (e.g., `class="heading_sf"`, `class_s1tb` for number, `class_s1tc` for title).
    *   **Sub-Section Headers:** Uses `<div>` elements with a class like `heading_s`.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Depth 3. Links to HTML files and specific anchors. Includes "Notes" sub-entries for each chapter, linking to anchors within the respective chapter files. Also contains a `<pageList>` section corresponding to the `page-map.xml`.
    *   **HTML ToC (`OEBPS/part0001.xhtml`):** Referenced in OPF guide.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses chapter-end notes (footnotes collected at the end of each chapter's HTML file).
    *   **Reference Markup (in main text):** `<a href="partXXXX.xhtml#anchorY" class="class_s1gu">N</a>`.
    *   **Note Text Location:** At the end of each chapter's HTML file, typically within a `<div>` (e.g., `<div class="class_s5w">`). Each note is often in its own `<div>` (e.g., `<div id="anchorY" class="class_s5b">...</div>`) starting with a linked number.

4.  **Citations/References (within note text):**
    *   Book/article titles often italicized using `<span class="class_s1gs">`.

5.  **Bibliography/Index:**
    *   "Index" linked in NCX to [`OEBPS/part0009.xhtml`](test_data/real_epubs/reading_hegel_zizek/OEBPS/part0009.xhtml).
    *   No explicit "Bibliography" entry in the NCX.

6.  **Page Number Markers:**
    *   Anchors like `<span id="aXXX"></span>` are used, corresponding to the `page-map.xml` and NCX `pageList`.

7.  **Emphasis:**
    *   Italics: `<span class="class_s1gs">`.

8.  **Embedded Fonts:**
    *   Not declared in the OPF manifest.

**Summary for "Reading Hegel":**
This EPUB 2 features chapter-end notes, with the NCX providing convenient navigation to these note sections. The inclusion of a `page-map.xml` is useful for print-digital correspondence. The HTML structure relies on `div` elements and classes for styling.
## 13. Marcuse - Reason and Revolution

**Source Directory:** [`test_data/real_epubs/reason_and_revolution/`](test_data/real_epubs/reason_and_revolution/)

**Date Analyzed:** 2025-05-08

**Key Files Examined:**
*   [`OPS/content.opf`](test_data/real_epubs/reason_and_revolution/OPS/content.opf)
*   [`OPS/toc.ncx`](test_data/real_epubs/reason_and_revolution/OPS/toc.ncx)
*   [`OPS/xhtml/11_p1_chapter01.xhtml`](test_data/real_epubs/reason_and_revolution/OPS/xhtml/11_p1_chapter01.xhtml) (Chapter 1 example)

**Overall Structure:**
*   EPUB 2 format.
*   Content files and resources are located within an `OPS/` directory, with text content in `OPS/xhtml/`, styles in `OPS/styles/`, and fonts in `OPS/fonts/`.
*   Filenames are descriptive and prefixed with numbers indicating order (e.g., `11_p1_chapter01.xhtml`).
*   Includes embedded `.otf` (OpenType) fonts (Linux Libertine).
*   Includes `.xpgt` (XML Page Template) files, suggesting professional authoring tools.
*   Contains Calibre metadata.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Chapter Number:** `<h1>` with class `chapnum`.
    *   **Chapter Title:** `<h1>` with class `chaptita`.
    *   (Sub-section headers within chapters to be confirmed by examining more files, but NCX suggests they exist and are linked via anchors).

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. `dtb:depth` is "1" but shows up to 3 levels of nesting (Part -> Chapter -> Section). Links to HTML files and specific anchors (e.g., `#p1-i-1`).
    *   **HTML ToC (`OPS/xhtml/08_contents.xhtml`):** Referenced in OPF guide.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses same-page footnotes (notes appear at the end of the XHTML file where they are referenced).
    *   **Reference Markup (in main text):** `<sup><a href="#foot_X" id="foot-X">N</a></sup>`.
    *   **Note Text Location:** At the bottom of each content XHTML file, using `<p class="footnote">`. Each note begins with a linked number: `<a href="#foot-X" id="foot_X">N</a>`.

4.  **Citations/References (within note text):**
    *   (To be confirmed by looking at more note examples, but likely standard text formatting with italics for titles).

5.  **Bibliography/Index:**
    *   "Bibliography" ([`xhtml/23_biblio.xhtml`](test_data/real_epubs/reason_and_revolution/OPS/xhtml/23_biblio.xhtml)) and "Index" ([`xhtml/24_index.xhtml`](test_data/real_epubs/reason_and_revolution/OPS/xhtml/24_index.xhtml)) are separate files linked in the NCX.

6.  **Page Number Markers:**
    *   Embedded using `<a id="page_X"/>`.

7.  **Emphasis:**
    *   Italics: `<em>`.
    *   Small Caps: `<span class="smallcaps">`.

8.  **Embedded Fonts:**
    *   Linux Libertine `.otf` fonts are listed in the OPF manifest (media type declared as `application/octet-stream`).

9.  **Images:**
    *   Used for chapter decorations and potentially figures/tables (e.g., `chapimage.jpg`, `figX-XX.jpg`).

**Summary for "Reason and Revolution":**
This EPUB 2 is well-structured with clear file naming and organization. It uses same-page footnotes collected at the end of each chapter's XHTML file. Embedded OpenType fonts and publisher-specific template files (`.xpgt`) are present.
## 13. Marcuse - Reason and Revolution

**Source Directory:** [`test_data/real_epubs/reason_and_revolution/`](test_data/real_epubs/reason_and_revolution/)

**Date Analyzed:** 2025-05-08 (Re-confirmed)

**Key Files Examined:**
*   [`OPS/content.opf`](test_data/real_epubs/reason_and_revolution/OPS/content.opf)
*   [`OPS/toc.ncx`](test_data/real_epubs/reason_and_revolution/OPS/toc.ncx)
*   [`OPS/xhtml/11_p1_chapter01.xhtml`](test_data/real_epubs/reason_and_revolution/OPS/xhtml/11_p1_chapter01.xhtml) (Chapter 1 example)

**Overall Structure:**
*   EPUB 2 format.
*   Content files and resources are located within an `OPS/` directory, with text content in `OPS/xhtml/`, styles in `OPS/styles/`, and fonts in `OPS/fonts/`.
*   Filenames are descriptive and prefixed with numbers indicating order (e.g., `11_p1_chapter01.xhtml`).
*   Includes embedded `.otf` (OpenType) fonts (Linux Libertine).
*   Includes `.xpgt` (XML Page Template) files, suggesting professional authoring tools.
*   Contains Calibre metadata (likely added post-production if `.xpgt` files were from original authoring).
*   A `page-map.xml` is present in the root and referenced in the OPF spine for print page navigation.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Chapter Number:** `<h1>` with class `chapnum` (e.g., `<h1 class="chapnum"><a id="page_30"/>I</h1>`).
    *   **Chapter Title:** `<h1>` with class `chaptita` (e.g., `<h1 class="chaptita">Hegel’s Early Theological Writings (1790-1800)</h1>`).
    *   **Part Titles/Section Headers within Chapters:** The NCX indicates these exist (e.g., "1. The Socio-Historical Setting" within an Introduction part) and link to anchors within chapter files. Their specific HTML markup likely uses `<h2>` or `<h3>` with appropriate classes.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. The `dtb:depth` metadata is "1", but the `navMap` shows up to three levels of nesting (Part -> Chapter -> Section). Links to HTML files and specific anchors (e.g., `xhtml/10_p1_introduction.xhtml#p1-i-1`).
    *   **HTML ToC (`OPS/xhtml/08_contents.xhtml`):** Referenced in OPF guide.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses same-page footnotes (notes appear at the end of the XHTML file where they are referenced).
    *   **Reference Markup (in main text):** `<sup><a href="#foot_X" id="foot-X">N</a></sup>` (e.g., `<sup><a href="#foot_1" id="foot-1">1</a></sup>`).
    *   **Note Text Location:** At the bottom of each content XHTML file, typically within `<p class="footnote">`. Each note begins with a linked number: `<a href="#foot-X" id="foot_X">N</a>`.

4.  **Citations/References (within note text):**
    *   Titles often italicized using `<em>`. Other details are plain text.

5.  **Bibliography/Index:**
    *   "Bibliography" ([`xhtml/23_biblio.xhtml`](test_data/real_epubs/reason_and_revolution/OPS/xhtml/23_biblio.xhtml)) and "Index" ([`xhtml/24_index.xhtml`](test_data/real_epubs/reason_and_revolution/OPS/xhtml/24_index.xhtml)) are separate files linked in the NCX.

6.  **Page Number Markers:**
    *   Embedded using `<a id="page_X"/>`. These correspond to the `page-map.xml` and the NCX `pageList`.

7.  **Emphasis:**
    *   Italics: `<em>`.
    *   Small Caps: `<span class="smallcaps">`.

8.  **Embedded Fonts:**
    *   Linux Libertine `.otf` fonts are listed in the OPF manifest. The `media-type` is declared as `application/octet-stream`, though `application/vnd.ms-opentype` or `application/font-sfnt` would be more specific.

9.  **Images:**
    *   Used for chapter decorations (e.g., `chapimage.jpg`) and potentially figures/tables (e.g., `figX-XX.jpg`, `tabXX-XX.jpg` listed in the directory).

**Summary for "Reason and Revolution":**
This EPUB 2 is well-structured with clear file naming and organization. It uses same-page footnotes collected at the end of each chapter's XHTML file. Embedded OpenType fonts and publisher-specific template files (`.xpgt`) are present. The NCX provides a hierarchical ToC, and a `page-map.xml` facilitates print page navigation. The `dtb:depth` in NCX is inconsistent with the actual nesting.
## 14. Franz Rosenzweig - Hegel and the State

**Source Directory:** [`test_data/real_epubs/rosenzweigh_hegel_and_the_state/`](test_data/real_epubs/rosenzweigh_hegel_and_the_state/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`ops/content.opf`](test_data/real_epubs/rosenzweigh_hegel_and_the_state/ops/content.opf) (Analyzed in previous step)
*   [`ops/xhtml/nav.xhtml`](test_data/real_epubs/rosenzweigh_hegel_and_the_state/ops/xhtml/nav.xhtml)
*   [`ops/xhtml/C_008_c1.xhtml`](test_data/real_epubs/rosenzweigh_hegel_and_the_state/ops/xhtml/C_008_c1.xhtml) (Chapter 1 example)
*   [`ops/xhtml/A_006_foreword1.xhtml`](test_data/real_epubs/rosenzweigh_hegel_and_the_state/ops/xhtml/A_006_foreword1.xhtml) (Foreword example with bibliography)

**Overall Structure:**
*   EPUB 3 format.
*   Content files and resources are located within an `ops/` directory, with subdirectories for `styles/` and `xhtml/`.
*   Uses an EPUB 3 Navigation Document (`nav.xhtml`) with `epub:type="toc"`, `epub:type="landmarks"`, and `epub:type="page-list"`.
*   No separate `toc.ncx` was explicitly mentioned in the `content.opf`'s spine or guide (based on previous analysis step).
*   CSS is in `ops/styles/9781000993080.css`.
*   Contains `Adept.expected.resource` meta tags in content XHTML files.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` in `content.opf`. The `nav.xhtml` file itself has `<title>Navigational Table of Contents</title>`.
    *   **Chapter Title/Number:** In content files (e.g., `C_008_c1.xhtml`), chapter titles are `<h1>` with class "chapter" (e.g., `<h1 class="chapter" id="c1">...</h1>`). The chapter number is typically nested within spans like `<span class="cn"><span class="bor">N</span></span>`.
    *   **Foreword Title:** `<h1>` with class "fmt" (e.g., `<h1 class="fmt" id="f1">...</h1>` in `A_006_foreword1.xhtml`).
    *   **Sub-headers:** Not explicitly tagged with `<h2>`, `<h3>` in the sample content file `C_008_c1.xhtml`. The `nav.xhtml` creates a deep hierarchy by linking to fragment identifiers (e.g., `#p17`, `#p18`) within chapter files, suggesting these anchors mark conceptual sub-sections.

2.  **Table of Contents (ToC):**
    *   **EPUB 3 Nav Doc (`ops/xhtml/nav.xhtml`):**
        *   `epub:type="toc"`: Primary navigation. Deeply nested `<ol class="none">` structure. Links point to XHTML files, often with fragment identifiers (e.g., `A_006_foreword1.xhtml#f1`, `C_008_c1.xhtml#p17`).
        *   `epub:type="landmarks"`: Provides links to key sections (cover, title page, toc, foreword, preface, bodymatter, backmatter, bibliography, index) using `epub:type` attributes on `<a>` tags.
        *   `epub:type="page-list"`: A hidden list of `<a>` tags linking to page number anchors within content files.
    *   **HTML ToC (Formatted):** The file `A_005_toc.xhtml` is linked as the "Table of Contents" in the `nav.xhtml` landmarks section and also appears in the `epub:type="toc"` navigation.

3.  **Footnotes/Endnotes/Bibliographic References:**
    *   **Type:** The examined foreword (`A_006_foreword1.xhtml`) uses **bibliographic references** embedded within the text, linking to a bibliography section at the end of the *same file*.
    *   **Reference Markup (in foreword):** `<a epub:type="biblioref" href="A_006_foreword1.xhtml#r0_X" id="r0_Xb" role="doc-biblioref">Author Year</a>`.
    *   **Bibliography Section (in foreword):** A `<section epub:type="bibliography" role="doc-bibliography">` containing an `<ul class="none">`.
    *   **Bibliography Entry:** Each entry is an `<li epub:type="biblioentry" id="r0_X">`. These entries contain `<cite>` tags for titles and an `epub:type="backlink"` `<a>` tag that links back to the first in-text citation.
    *   Traditional footnotes (superscript numbers linking to bottom of page or a separate endnotes file) were not observed in the samples `C_008_c1.xhtml` or `A_006_foreword1.xhtml`.

4.  **Emphasis:**
    *   Italics: `<i>` tags (e.g., in `A_006_foreword1.xhtml` for book titles within the text).
    *   No bold tags (`<b>` or `<strong>`) were observed for general emphasis in the sampled content paragraphs, though chapter numbers used a class that might imply bolding via CSS.

5.  **Page Number Markers:**
    *   Present as `<span aria-label=" page X. " epub:type="pagebreak" id="pX" role="doc-pagebreak"/>` or `<span aria-label=" page roman_num. " epub:type="pagebreak" id="p_roman_num" role="doc-pagebreak"/>` (e.g., `id="pxv"` in `A_006_foreword1.xhtml`, `id="p17"` in `C_008_c1.xhtml`).

6.  **Other Notable Features:**
    *   **Index Term Markers:** `<span id="indx-termXXXX"/>` found in `C_008_c1.xhtml` (e.g., `<span id="indx-term2396"/>`). These appear to be anchors for an index and do not contain visible text.
    *   **DOI Link:** Present in the header of `C_008_c1.xhtml`: `<p class="doi">DOI: <a ...>...</a></p>`.
    *   **Credit Span:** `<span epub:type="credit" role="doc-credit">` used in `A_006_foreword1.xhtml` for attributing a quote.
    *   **Blockquotes:** Standard `<blockquote>` elements are used.

**Summary for "Hegel and the State" (Franz Rosenzweig):**
This EPUB 3 is well-structured, featuring a comprehensive `nav.xhtml` that provides ToC, landmarks, and a page list. The examined foreword uses in-text bibliographic references that link to a bibliography section within the same file, a distinct style from traditional footnotes. Chapter content uses `<h1>` for titles, and page breaks are clearly marked with `epub:type="pagebreak"`. Index terms are embedded as empty spans with IDs. The hierarchy of sub-sections within chapters is primarily defined by the `nav.xhtml` structure linking to fragment identifiers in the content files, rather than by explicit `<h2>`/`<h3>` tags in the sampled chapter content.
## 15. Byung-Chul Han - The Burnout Society

**Source Directory:** [`test_data/real_epubs/the_burnout_society/`](test_data/real_epubs/the_burnout_society/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`content.opf`](test_data/real_epubs/the_burnout_society/content.opf)
*   [`toc.ncx`](test_data/real_epubs/the_burnout_society/toc.ncx)
*   [`text/part0003.html`](test_data/real_epubs/the_burnout_society/text/part0003.html) ("Neuronal Power" chapter example)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files (`partXXXX.html`) are located in a `text/` subdirectory.
*   Standard Calibre metadata and structure.
*   Uses an NCX for ToC and an HTML ToC.
*   Endnotes are collected in a separate file.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Chapter/Section Titles (in content files):** Use `<p>` tags with specific classes (e.g., `<p class="c9">`) and nested `<strong>` for emphasis, rather than standard `<h1>-<h6>` tags (e.g., `<p class="c9" id="..."><strong class="calibre3">NEURONAL POWER</strong></p>`).

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Flat structure (all `navPoint`s are direct children of `navMap`), with each `navPoint` having `class="chapter"`. Links to `text/partXXXX.html` files. Includes entries for front matter, main content chapters, and a "Notes" section.
    *   **HTML ToC (`text/part0002.html`):** Referenced in the OPF `<guide>` section as "Contents".

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses endnotes.
    *   **Reference Markup (in main text):** `<sup>` tags (e.g., `<sup class="calibre7">`) containing an `<a>` tag that links to the notes file with a fragment identifier (e.g., `<a class="calibre4" href="part0011.html#id_146" id="id_145">1</a></sup>`).
    *   **Note Text Location:** All endnotes are collected in a dedicated HTML file, [`text/part0011.html`](test_data/real_epubs/the_burnout_society/text/part0011.html), as indicated by the NCX "Notes" entry and the `href` attributes in note references.

4.  **Emphasis:**
    *   Italics: `<em class="calibre2">`.
    *   Bold: Used for the main header via `<strong class="calibre3">`.

5.  **Page Number Markers:**
    *   Embedded as empty `<a>` tags with an `id` and a class (e.g., `<a class="calibre4" id="page_1"></a>`).

6.  **Other Notable Features:**
    *   Paragraphs use various classes (e.g., `p`, `c12`, `c13`, `c14`), likely for styling.
    *   Contains `Adept.expected.resource` meta tags in content XHTML files.

**Summary for "The Burnout Society":**
This EPUB 2, likely processed by Calibre, uses a flat NCX ToC and an HTML ToC. Chapter titles in content files are styled `<p>` tags rather than standard heading elements. It employs an endnote system where all notes are consolidated into a separate HTML file. Page numbers are marked with empty `<a>` tags.
## 16. Henry E. Allison - Kant's Transcendental Idealism: An Interpretation and Defense

**Source Directory:** [`test_data/real_epubs/allison_kants_transcendental_idealism/`](test_data/real_epubs/allison_kants_transcendental_idealism/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`OEBPS/content.opf`](test_data/real_epubs/allison_kants_transcendental_idealism/OEBPS/content.opf)
*   [`OEBPS/toc.ncx`](test_data/real_epubs/allison_kants_transcendental_idealism/OEBPS/toc.ncx)
*   [`OEBPS/Text/chapter_1.xhtml`](test_data/real_epubs/allison_kants_transcendental_idealism/OEBPS/Text/chapter_1.xhtml) (Chapter 1 example)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files (e.g., `cover.xhtml`, `chapter_1.xhtml`, `biblio.xhtml`) are located in an `OEBPS/Text/` subdirectory.
*   CSS files are in `OEBPS/Styles/`.
*   Images (cover) are in `OEBPS/Images/`.
*   Includes Calibre and Sigil metadata.
*   Uses an NCX for ToC. No separate HTML ToC explicitly guided in the OPF.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Chapter Titles (in content files):** `<h2>` with class `p-p1` and inline styles. The title text is within a nested `<span class="s-t2">` (e.g., `<h2 class="p-p1" ...><span class="s-t2" ...>Chapter 1. An Introduction to the Problem</span></h2>`).
    *   **Sub-headings (e.g., "I. KANTIAN ANTI-IDEALISM"):** Use `<p>` tags with specific classes (e.g., `p-p5`) and inline bold styling.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`OEBPS/toc.ncx`):** Primary navigation. Hierarchical with a depth of 3, reflecting Parts and Chapters. `navPoint` elements link directly to the XHTML files in `OEBPS/Text/` without fragment identifiers. Includes entries for front matter, parts, chapters, and bibliography.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses same-page footnotes.
    *   **Reference Markup (in main text):** `<sup><a id="ftn_refnum_chapter_X_N" href="#ftn_chapter_X_N">[N]</a></sup>`.
    *   **Note Text Location:** At the bottom of the same XHTML file where the reference occurs, typically after a `<hr/>` and a "Notes" heading (styled `<p>`). Each note is a `<p>` tag starting with `<sup><a id="ftn_chapter_X_N">[N]</a></sup>&nbsp;...note text...&nbsp;<a href="#ftn_refnum_chapter_X_N">Go back</a>`.

4.  **Emphasis:**
    *   Italics: `<span>` tags with specific classes (e.g., `s-t3`, `s-t4`) and/or inline `font-style: italic;`.
    *   Bold: Used for chapter titles and sub-headings via inline styles or specific span classes.

5.  **Page Number Markers:**
    *   Not observed in the sampled chapter file (`chapter_1.xhtml`). The NCX does not link to page numbers.

6.  **Bibliography:**
    *   A dedicated [`OEBPS/Text/biblio.xhtml`](test_data/real_epubs/allison_kants_transcendental_idealism/OEBPS/Text/biblio.xhtml) is listed in the OPF manifest and spine, and linked in the NCX.

7.  **Other Notable Features:**
    *   Heavy use of inline CSS styles on `<p>` and `<span>` tags throughout the content file, suggesting styling is not primarily offloaded to external CSS.
    *   No `epub:type` attributes were observed in the sampled content file.

**Summary for "Kant's Transcendental Idealism":**
This EPUB 2, likely processed by Calibre and Sigil, features a well-structured NCX ToC. It uses same-page footnotes with clear back-and-forth linking. Chapter and sub-headings are identified by specific tag/class combinations and inline styles rather than a strict hierarchy of `<h1>-<h6>` for all levels. The styling is heavily reliant on inline CSS.
## 17. Jean Baudrillard - Simulacra And Simulation

**Source Directory:** [`test_data/real_epubs/baudrillard_simulacra_and_simulation/`](test_data/real_epubs/baudrillard_simulacra_and_simulation/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`content.opf`](test_data/real_epubs/baudrillard_simulacra_and_simulation/content.opf)
*   [`toc.ncx`](test_data/real_epubs/baudrillard_simulacra_and_simulation/toc.ncx)
*   [`text/part1.xhtml`](test_data/real_epubs/baudrillard_simulacra_and_simulation/text/part1.xhtml) (HTML Table of Contents)
*   [`text/part2.xhtml`](test_data/real_epubs/baudrillard_simulacra_and_simulation/text/part2.xhtml) ("THE PRECESSION OF SIMULACRA" chapter example)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files (`partX.xhtml`) are located in a `text/` subdirectory.
*   Published by "ePub Bud".
*   The `content.opf` does not list any explicit CSS files in the manifest.
*   The first content file listed in the spine (`part1.xhtml`) is an HTML Table of Contents.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Chapter/Section Titles (in content files):** Appear as plain text directly within a `<div>`, followed by a `<br />` (e.g., `<div><a id="chapter2" name="chapter2"></a> THE PRECESSION OF SIMULACRA<br />...</div>`). Not standard `<h1>-<h6>` tags.
    *   **HTML ToC Title:** "TABLE OF CONTENTS" as plain text in `text/part1.xhtml`.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Flat structure (depth 1). `navPoint` elements link to `text/partX.xhtml` files with fragment identifiers (e.g., `text/part2.xhtml#chapter2`).
    *   **HTML ToC (`text/part1.xhtml`):** A simple, non-hyperlinked list of chapter titles as `<p>` tags, separated by `<br />` tags.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses endnotes located at the end of each chapter's XHTML file.
    *   **Reference Markup (in main text):** Superscripted numbers, sometimes prefixed with an asterisk (e.g., `*1`, `*2`), appear as plain text at the end of paragraphs. These are not hyperlinks.
    *   **Note Text Location:** At the end of the respective content file (e.g., `text/part2.xhtml`), under a plain text heading like "* NOTES *". Each note begins with its corresponding number.

4.  **Emphasis:**
    *   No `<em>`, `<i>`, `<strong>`, or `<b>` tags were observed for emphasis in the sampled content file (`text/part2.xhtml`). Styling is very minimal.

5.  **Page Number Markers:**
    *   Not observed in the sampled content file.

6.  **Other Notable Features:**
    *   Extensive use of `<br />` tags for spacing.
    *   The EPUB appears to be a basic conversion with minimal semantic HTML markup for structural elements like headers.
    *   The `dc:creator` field in the OPF is empty.

**Summary for "Simulacra And Simulation":**
This EPUB 2.0, published by ePub Bud, has a very basic structure. Chapter titles and sub-headings within content files are not marked with standard HTML header tags but are plain text. It uses a flat NCX for navigation. An unusual characteristic is the handling of endnotes: references are plain superscript text, and the note text itself is located at the end of the same chapter file, rather than in a consolidated notes section or linked via hyperlinks. The overall formatting is minimal.
## 18. Martin Buber - On Judaism

**Source Directory:** [`test_data/real_epubs/buber_on_judaism/`](test_data/real_epubs/buber_on_judaism/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`Bube_9780307834089_epub_opf_r1.opf`](test_data/real_epubs/buber_on_judaism/Bube_9780307834089_epub_opf_r1.opf)
*   [`Bube_9780307834089_epub_ncx_r1.ncx`](test_data/real_epubs/buber_on_judaism/Bube_9780307834089_epub_ncx_r1.ncx)
*   [`OEBPS/Bube_9780307834089_epub_c01_r1.htm`](test_data/real_epubs/buber_on_judaism/OEBPS/Bube_9780307834089_epub_c01_r1.htm) (Chapter I example)

**Overall Structure:**
*   EPUB 2.0 format.
*   OPF and NCX files are in the root directory. Content XHTML, CSS, images, and fonts are in the `OEBPS/` directory.
*   Filenames within `OEBPS/` are prefixed (e.g., `Bube_9780307834089_epub_`).
*   Includes embedded TTF fonts (CharisSIL variants).
*   Uses an NCX for ToC and an HTML ToC.
*   Endnotes are collected in a separate file.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Chapter Number (in content files):** `<h1>` with class `chapter` and an `id` (e.g., `c01`). The Roman numeral is within a `<span class="big">` and often padded with non-breaking spaces for centering.
    *   **Chapter Title (in content files):** A separate `<h1>` with class `chapter000`. Often includes an ornamental image (`<img>`) and the title text within `<em>` tags.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`Bube_9780307834089_epub_ncx_r1.ncx`):** Primary navigation. Hierarchical (depth 2), reflecting Parts and Chapters/Sections. `navPoint` elements have classes like "part", "chapter", "other". Links point directly to XHTML files in `OEBPS/` without fragment identifiers.
    *   **HTML ToC ([`OEBPS/Bube_9780307834089_epub_toc_r1.htm`](test_data/real_epubs/buber_on_judaism/OEBPS/Bube_9780307834089_epub_toc_r1.htm)):** Referenced in the OPF `<guide>` section.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses endnotes.
    *   **Reference Markup (in main text):** `<a>` tags with class `hlink`, an `id` (e.g., `c01-nts1a`), and an `href` pointing to an anchor in the notes file (`Bube_9780307834089_epub_nts_r1.htm#c01-nts1`). The link text is a superscripted number within `<sup class="frac">`.
    *   **Note Text Location:** All endnotes are collected in a dedicated HTML file, [`OEBPS/Bube_9780307834089_epub_nts_r1.htm`](test_data/real_epubs/buber_on_judaism/OEBPS/Bube_9780307834089_epub_nts_r1.htm), as indicated by the NCX "Notes" entry and `href` attributes.

4.  **Emphasis:**
    *   Italics: `<em>` tags (used for chapter titles and in-text emphasis).
    *   Small caps for first word: `<span class="small">` on the first letter(s) of the first paragraph of a chapter.

5.  **Page Number Markers:**
    *   Embedded as empty `<a>` tags with an `id` (e.g., `<a id="page11"/>`).

6.  **Embedded Fonts:**
    *   TTF font files (CharisSIL variants) are listed in the OPF manifest and located in `OEBPS/fonts/`.

7.  **Other Notable Features:**
    *   Use of Adobe page template (`page-template.xpgt`).
    *   `Adept.resource` meta tag in content files.
    *   Paragraphs typically have `class="indent"`.

**Summary for "On Judaism":**
This is a professionally produced EPUB 2.0 with a clear hierarchical structure defined in the NCX. It uses endnotes collected in a separate file, with hyperlinked references. Chapter titles are distinctively styled using `<h1>` tags, images, and emphasis. The EPUB embeds fonts, which will influence text rendering.
## 19. Gilles Deleuze and Felix Guattari - Anti-Oedipus

**Source Directory:** [`test_data/real_epubs/deleuze_antioedipus/`](test_data/real_epubs/deleuze_antioedipus/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`content.opf`](test_data/real_epubs/deleuze_antioedipus/content.opf)
*   [`toc.ncx`](test_data/real_epubs/deleuze_antioedipus/toc.ncx)
*   [`index_split_000.html`](test_data/real_epubs/deleuze_antioedipus/index_split_000.html) (Title/Cover Page)
*   [`index_split_001.html`](test_data/real_epubs/deleuze_antioedipus/index_split_001.html) (Front Matter - Preface title, Copyright, Acknowledgments, "CONTENTS" heading)
*   [`index_split_003.html`](test_data/real_epubs/deleuze_antioedipus/index_split_003.html) (Introduction by Mark Seem &amp; HTML ToC)
*   [`index_split_004.html`](test_data/real_epubs/deleuze_antioedipus/index_split_004.html) (Preface content by Foucault)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files (`index_split_XXX.html`), OPF, NCX, CSS, and images are all in the root directory.
*   Heavily segmented content files, characteristic of Calibre processing from a PDF (generator listed as "pdftohtml 0.36" in HTML meta tags).
*   The NCX is extremely minimal, offering almost no navigation.
*   A detailed, non-hyperlinked HTML Table of Contents is present in `index_split_003.html`.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** "Anti-Oedipus" (from OPF/NCX). Series title "CAPITALISM AND SCHIZOPHRENIA" appears on the title page (`index_split_000.html`).
    *   **Major Section Headers (e.g., Preface, Introduction, main ToC sections):** Use `<h2>` (e.g., `<h2 class="calibre4"...>PREFACE by Michel Foucault</h2>`) or are styled `<p>` tags.
    *   **Sub-headers within ToC/Content:** Typically `<p class="calibre2">` tags, with visual hierarchy likely managed by CSS or manual line breaks. Some use `<b class="calibre3">`.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Contains only a single "Start" entry pointing to `index_split_000.html`. Not useful for navigating the book's structure.
    *   **HTML ToC (in `index_split_003.html`):** A detailed, multi-level textual table of contents. Entries are `<p class="calibre2">` tags. Page numbers are included as italicized text (e.g., `<i class="calibre5">16</i>`). This ToC is not hyperlinked.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses same-file footnotes (non-hyperlinked).
    *   **Reference Markup (in Preface `index_split_004.html`):** A plain text asterisk `*` at the end of a paragraph.
    *   **Note Text Location (in Preface `index_split_004.html`):** The corresponding note text appears at the bottom of the same file, as a `<p class="calibre2">` starting with an asterisk.

4.  **Emphasis:**
    *   Italics: `<i class="calibre5">` or `<i class="calibre6">`.
    *   Bold: `<b class="calibre3">`.

5.  **Page Number Markers:**
    *   Page numbers from the source PDF (e.g., "xl", "xli") are embedded as plain text within `<p class="calibre2">` tags in the preface content (`index_split_004.html`), often interrupting the flow of text from a previous split file. No semantic page break tags observed.

6.  **Other Notable Features:**
    *   The EPUB is a direct conversion from PDF, leading to many small HTML files and preservation of PDF page number text.
    *   Styling is basic, relying on `stylesheet.css` and `page_styles.css`.
    *   The `<guide>` section in the OPF is empty.

**Summary for "Anti-Oedipus":**
This EPUB is a challenging case for RAG due to its PDF origins and minimal semantic structure. The NCX is uninformative. Navigation relies on a non-hyperlinked HTML ToC found within one of the early split files. Footnotes are present but not hyperlinked. Headers are often styled `<p>` tags rather than standard `<h1>-<h6>`. The numerous small, split files and embedded PDF page numbers would require careful handling during processing.
## 20. Jacques Derrida - Specters of Marx

**Source Directory:** [`test_data/real_epubs/derrida_spectres_of_marx/`](test_data/real_epubs/derrida_spectres_of_marx/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`OEBPS/content.opf`](test_data/real_epubs/derrida_spectres_of_marx/OEBPS/content.opf)
*   [`OEBPS/toc.ncx`](test_data/real_epubs/derrida_spectres_of_marx/OEBPS/toc.ncx)
*   [`OEBPS/12_chapter-title-1.html`](test_data/real_epubs/derrida_spectres_of_marx/OEBPS/12_chapter-title-1.html) ("1. Injunctions of Marx" chapter example)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files, CSS, images, and fonts are in the `OEBPS/` directory.
*   Filenames for XHTML content use a numerical prefix and descriptive suffix (e.g., `01_cover.html`, `12_chapter-title-1.html`).
*   Includes embedded TTF fonts (DejaVu variants).
*   Uses an NCX for ToC and an HTML ToC (referenced in OPF guide).
*   Endnotes are collected in a separate file.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** "Specters of Marx" (from OPF/NCX).
    *   **Chapter Number (in content files):** `<p class="chapter-number_1">` containing a bolded number within an `<a>` tag that links back to the HTML ToC (e.g., `<a href="06_toc-title.html#pg-23-1"><b>1</b></a>`).
    *   **Chapter Title (in content files):** `<p class="chapter-title_2">` containing a bolded title within an `<a>` tag that also links back to the HTML ToC (e.g., `<a href="06_toc-title.html#pg-23-1"><b>INJUNCTIONS OF MARX</b></a>`).
    *   An ornamental image is often placed between the chapter number and title.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`OEBPS/toc.ncx`):** Primary navigation. Flat structure (depth 1). `navPoint` elements link directly to XHTML files in `OEBPS/` without fragment identifiers. Includes entries for front matter, chapters, notes, and index.
    *   **HTML ToC ([`OEBPS/06_toc-title.html`](test_data/real_epubs/derrida_spectres_of_marx/OEBPS/06_toc-title.html)):** Referenced in the OPF `<guide>` section. (Structure not examined in detail, but chapter content links point to anchors within it).

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses endnotes.
    *   **Reference Markup (in main text):** `<sup>` tags with class `endnotecall` containing an `<a>` tag. The `<a>` tag has an `id` (e.g., `pg-24-117`) and an `href` pointing to an anchor in the endnotes file (`17_endnote-title.html#pg-246-148`). The link text is the note number.
    *   **Note Text Location:** All endnotes are collected in a dedicated HTML file, [`OEBPS/17_endnote-title.html`](test_data/real_epubs/derrida_spectres_of_marx/OEBPS/17_endnote-title.html), as indicated by the NCX "Notes" entry and `href` attributes in note references.

4.  **Emphasis:**
    *   Italics: `<i>` tags.
    *   Bold: `<b>` tags (used for chapter numbers/titles).

5.  **Page Number Markers:**
    *   Embedded as empty `<a>` tags with an `id` like `pl-XX-Y` (e.g., `<a id="pl-23-1"/>`). These seem to be internal layout markers.

6.  **Embedded Fonts:**
    *   TTF font files (DejaVu variants) are listed in the OPF manifest and located in `OEBPS/fonts/`.

7.  **Other Notable Features:**
    *   Use of Adobe page template (`page-template.xpgt`).
    *   `Adept.expected.resource` meta tag in content files.
    *   Paragraphs use various classes like `body-text`, `body-text_1`, `disp-quote_3`, etc.

**Summary for "Specters of Marx":**
This is a professionally produced EPUB 2.0. It features a flat NCX but also an HTML ToC which chapter headings link back to. Endnotes are hyperlinked and collected in a dedicated file. The EPUB embeds DejaVu fonts. Chapter headings are styled `<p>` tags rather than standard `<h1>-<h6>` elements.
## 21. Jacques Derrida - The Gift of Death &amp; Literature in Secret

**Source Directory:** [`test_data/real_epubs/derrida_the_gift_of_death/`](test_data/real_epubs/derrida_the_gift_of_death/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`OEBPS/content.opf`](test_data/real_epubs/derrida_the_gift_of_death/OEBPS/content.opf)
*   [`OEBPS/toc.ncx`](test_data/real_epubs/derrida_the_gift_of_death/OEBPS/toc.ncx)
*   [`OEBPS/Text/chapter0007.html`](test_data/real_epubs/derrida_the_gift_of_death/OEBPS/Text/chapter0007.html) ("One. Secrets of European Responsibility" chapter example)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files (`chapterXXXX.html`, `coverpage.xhtml`) are in an `OEBPS/Text/` subdirectory.
*   CSS is in `OEBPS/Styles/`, images in `OEBPS/Images/`.
*   Metadata indicates conversion by "ScribdMpubToEpubConverter".
*   Uses an NCX for ToC. The OPF guide is empty, so no separate HTML ToC is explicitly guided.
*   Endnotes are collected in a separate file.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** "The Gift of Death &amp; Literature in Secret: Second Edition" (from OPF/NCX).
    *   **Chapter Number (in content files):** `<h3>` tag (e.g., `<h3>ONE</h3>`).
    *   **Chapter Title (in content files):** `<h2>` tag (e.g., `<h2>Secrets of European Responsibility</h2>`).
    *   Standard HTML header tags are used for chapter titles/numbers.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`OEBPS/toc.ncx`):** Primary navigation. Flat structure (depth 1). `navPoint` elements link directly to XHTML files in `OEBPS/Text/` without fragment identifiers. Includes entries for front matter, main sections/chapters, and a "Notes" section.
    *   **HTML ToC:** An entry for "Contents" in the NCX links to `Text/chapter0004.html`, suggesting this file serves as the HTML ToC.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses endnotes.
    *   **Reference Markup (in main text):** Plain text superscripted numbers (e.g., ¹, ², ³). These are not hyperlinked.
    *   **Note Text Location:** The NCX lists a "Notes" section linking to `Text/chapter0016.html`. It is assumed the plain text superscript references correspond to endnotes in this dedicated file.

4.  **Emphasis:**
    *   Italics: `<i>` tags.

5.  **Page Number Markers:**
    *   Not observed in the sampled content file.

6.  **Embedded Fonts:**
    *   No embedded fonts are listed in the OPF manifest.

7.  **Other Notable Features:**
    *   Use of Adobe page template (`page-template.xpgt`).
    *   `Adept.resource` meta tag in content files.
    *   Paragraphs sometimes have a class `style1`.
    *   Forced page breaks using `<div style="page-break-before: always;" />`.

**Summary for "The Gift of Death &amp; Literature in Secret":**
This EPUB 2.0, likely a conversion from a digital platform (Scribd), uses standard HTML heading tags for chapters. It employs an endnote system with a dedicated notes file, though the in-text references are plain superscript numbers without hyperlinks. The NCX provides a flat navigation structure.
## 22. Michael Hardt &amp; Antonio Negri - Empire

**Source Directory:** [`test_data/real_epubs/empire_hardt_negri/`](test_data/real_epubs/empire_hardt_negri/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`OEBPS/content.opf`](test_data/real_epubs/empire_hardt_negri/OEBPS/content.opf)
*   [`OEBPS/toc.ncx`](test_data/real_epubs/empire_hardt_negri/OEBPS/toc.ncx)
*   [`OEBPS/Text/index_split_002.html`](test_data/real_epubs/empire_hardt_negri/OEBPS/Text/index_split_002.html) (Part 1 / Section 1.1 example)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files (`index_split_XXX.html`, `cover.xhtml`) are in an `OEBPS/Text/` subdirectory.
*   CSS is in `OEBPS/Styles/`, images in `OEBPS/Images/`.
*   Includes Calibre and Sigil metadata.
*   Uses an NCX for ToC. The OPF guide only references a cover page.
*   Endnotes are likely collected in a separate file.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** "Empire" (from OPF/NCX).
    *   **Part Titles (in content files):** `<h2>` with class `calibre2` and an `id` (e.g., `id="calibre_toc_1"` for "PART 1...").
    *   **Section Titles (in content files):** Also `<h2>` with class `calibre2` and an `id` (e.g., `id="calibre_pb_1"` for "1.1 - WORLD ORDER"). The NCX `navLabel` text provides the distinction between Part and Section.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`OEBPS/toc.ncx`):** Primary navigation. Technically flat (depth 1), but `navLabel` text implies a hierarchy (e.g., "PART 1", then "1.1", "1.2"). Links point to `Text/index_split_XXX.html` files, sometimes with fragment identifiers (e.g., `#calibre_pb_1`, `#sigil_toc_id_1`). Includes entries for Preface, Parts, sections within Parts, an Intermezzo, and Notes.
    *   **HTML ToC:** No explicit HTML ToC file is referenced in the OPF `<guide>` section (only a cover).

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses endnotes.
    *   **Reference Markup (in main text):** Plain text bracketed numbers (e.g., `[1]`, `[2]`). These are not hyperlinked.
    *   **Note Text Location:** The NCX lists a "NOTES" section linking to `Text/index_split_017.html`. It is assumed the plain text bracketed references correspond to endnotes in this dedicated file.

4.  **Emphasis:**
    *   No `<em>`, `<i>`, `<strong>`, or `<b>` tags were observed for emphasis in the sampled content file. Styling is likely handled by external CSS.

5.  **Page Number Markers:**
    *   Not observed in the sampled content file.

6.  **Embedded Fonts:**
    *   No embedded fonts are listed in the OPF manifest.

7.  **Other Notable Features:**
    *   The EPUB is heavily segmented into `index_split_XXX.html` files, typical of Calibre processing.
    *   Epigraphs are formatted as simple `<p class="calibre1">` tags.

**Summary for "Empire":**
This EPUB 2.0, processed by Calibre and Sigil, relies on `<h2>` tags for both Part and Section titles, with the NCX `navLabel` text providing the hierarchical distinction. Endnote references are plain text bracketed numbers, with the notes expected in a separate file. The content is heavily split into numerous small HTML files.
## 23. Michel Foucault - Archaeology of Knowledge

**Source Directory:** [`test_data/real_epubs/foucault_archaeology_of_knowledge/`](test_data/real_epubs/foucault_archaeology_of_knowledge/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`OEBPS/content.opf`](test_data/real_epubs/foucault_archaeology_of_knowledge/OEBPS/content.opf)
*   [`OEBPS/toc.ncx`](test_data/real_epubs/foucault_archaeology_of_knowledge/OEBPS/toc.ncx)
*   [`OEBPS/008_9780203604168_chapter1.html`](test_data/real_epubs/foucault_archaeology_of_knowledge/OEBPS/008_9780203604168_chapter1.html) ("1 The Unities of Discourse" chapter example)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files, CSS, images, and fonts are in the `OEBPS/` directory.
*   Filenames for XHTML content use a numerical prefix and descriptive suffix (e.g., `000_9780203604168_cover.html`, `008_9780203604168_chapter1.html`).
*   Includes embedded TTF fonts (Arial, Times variants).
*   Uses an NCX for ToC and an HTML ToC (referenced in NCX and spine).
*   Footnotes are same-page and hyperlinked.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** "Archaeology of Knowledge" (from OPF). NCX `docTitle` incorrectly lists "Michel Foucault".
    *   **Chapter Title/Number (in content files):** `<h1>` with class `paracenter` and an `id` (e.g., `ch1`). Contains the chapter number, an ornamental line ("________________"), and the chapter title. Example: `<h1 class="paracenter" id="ch1"><a id="p23"/>1<br/>________________<br/>THE UNITIES OF DISCOURSE</h1>`.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`OEBPS/toc.ncx`):** Primary navigation. Hierarchical (depth 2 indicated in metadata, but nesting observed), reflecting Parts and Chapters/Sections. `navPoint` elements link to XHTML files, often with fragment identifiers (e.g., `#ch1`).
    *   **HTML ToC ([`OEBPS/004_9780203604168_contents.html`](test_data/real_epubs/foucault_archaeology_of_knowledge/OEBPS/004_9780203604168_contents.html)):** Referenced in the NCX.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses same-page footnotes.
    *   **Reference Markup (in main text):** `<a>` tag with an `id` (e.g., `ch1-fn1`) and an `href` pointing to the note anchor (e.g., `#ch1-fnref1`), containing a superscripted number: `<a href="#ch1-fnref1" id="ch1-fn1"><sup>1</sup></a>`.
    *   **Note Text Location:** At the bottom of the same XHTML file. Each note is a `<p class="fn">`. The note text starts with `<span class="spanlabel"><a href="#ch1-fn1" id="ch1-fnref1">1</a></span>` (linking back to the reference) followed by `<span class="spanbody">...note text...</span>`.

4.  **Emphasis:**
    *   Italics: `<i>` tags.
    *   Bold: `<b>` tags (used in chapter titles).

5.  **Page Number Markers:**
    *   Embedded as empty `<a>` tags with an `id` like `pXX` (e.g., `<a id="p23"/>`).

6.  **Embedded Fonts:**
    *   TTF font files (Arial, Times variants) are listed in the OPF manifest and located in `OEBPS/fonts/`.

7.  **Other Notable Features:**
    *   Use of Adobe page template (`page-template.xpgt`).
    *   `Adept.expected.resource` meta tag in content files.
    *   Paragraphs use classes `paranoindent1` and `paraindent1`.

**Summary for "Archaeology of Knowledge":**
This is a well-structured EPUB 2.0. It uses standard HTML headers for chapters and a robust, hyperlinked same-page footnote system. The NCX provides good hierarchical navigation. The EPUB embeds common fonts.
## 24. Martin Heidegger - Basic Questions of Philosophy

**Source Directory:** [`test_data/real_epubs/heidegger_basic_questions/`](test_data/real_epubs/heidegger_basic_questions/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`OEBPS/content.opf`](test_data/real_epubs/heidegger_basic_questions/OEBPS/content.opf)
*   [`OEBPS/toc.ncx`](test_data/real_epubs/heidegger_basic_questions/OEBPS/toc.ncx)
*   [`OEBPS/xhtml/09_Chapter01.xhtml`](test_data/real_epubs/heidegger_basic_questions/OEBPS/xhtml/09_Chapter01.xhtml) (Chapter 1 example)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files, CSS, images, and page template are in the `OEBPS/` directory, organized into `xhtml/`, `styles/`, and `images/` subdirectories.
*   Uses an NCX for ToC, which includes a detailed page list. An HTML ToC is also referenced in the OPF guide.
*   No embedded fonts are listed in the OPF.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** "Basic Questions of Philosophy: Selected “Problems” of “Logic”" (from OPF/NCX).
    *   **Chapter Titles (in content files):** Composed of two `<p>` tags. The first (`<p class="chno">`) contains the chapter number (e.g., "<i>Chapter One</i>"). The second (`<p class="chtitle">`) contains the chapter title text (e.g., "Preliminary Interpretation of the Essence of Philosophy").
    *   **Section Headers (e.g., §1, §2):** Use `<p class="h1">` tags. The section number and title are within this tag, often with bold and italic styling applied via `<b>` and `<i>` tags. Example: `<p class="h1"><a id="ch1_1"/><b>§1. <i>Futural philosophy...</i></b></p>`.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`OEBPS/toc.ncx`):** Primary navigation. Very detailed and hierarchical (metadata claims depth 5, and nesting reflects this). Includes `navPoint`s for Parts, Chapters, and numbered/lettered sub-sections (e.g., §1, a), Recapitulation 1)). Links point to XHTML files, often with specific fragment identifiers (e.g., `xhtml/09_Chapter01.xhtml#ch1_1`).
    *   **HTML ToC ([`OEBPS/xhtml/06_Contents.xhtml`](test_data/real_epubs/heidegger_basic_questions/OEBPS/xhtml/06_Contents.xhtml)):** Referenced in the OPF `<guide>` section.
    *   **Page List:** A comprehensive `<pageList>` is present in the NCX, mapping print page numbers to anchors in the content files.

3.  **Footnotes/Endnotes:**
    *   No footnote or endnote references were observed in the sampled chapter file (`09_Chapter01.xhtml`). The NCX does not explicitly list a separate "Notes" section, though an "Appendix" is present.

4.  **Emphasis:**
    *   Italics: `<i>` tags.
    *   Bold: `<b>` tags.

5.  **Page Number Markers:**
    *   Embedded as empty `<a>` tags with an `id` like `page_X` (e.g., `<a id="page_3"/>`). These correspond to the NCX `pageList`.

6.  **Embedded Fonts:**
    *   No embedded fonts are listed in the OPF manifest.

7.  **Other Notable Features:**
    *   Use of Adobe page template (`styles/page-template.xpgt`).
    *   `Adept.expected.resource` meta tag in content files.
    *   Paragraphs use classes `noindent` and `indent`.

**Summary for "Basic Questions of Philosophy":**
This EPUB 2.0 is well-structured, particularly its NCX which provides deep, granular navigation and a full page list. Chapter and section headings are styled `<p>` tags rather than standard HTML heading elements. No traditional footnotes/endnotes were found in the examined sample, which is unusual for a philosophical text of this nature; notes might be integrated differently or absent.
## 25. Martin Heidegger - Ponderings VII–XI (Black Notebooks)

**Source Directory:** [`test_data/real_epubs/heidegger_black_notebooks_VII_XI/`](test_data/real_epubs/heidegger_black_notebooks_VII_XI/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`OEBPS/9780253025036.opf`](test_data/real_epubs/heidegger_black_notebooks_VII_XI/OPS/9780253025036.opf)
*   [`OEBPS/toc.ncx`](test_data/real_epubs/heidegger_black_notebooks_VII_XI/OPS/toc.ncx)
*   [`OEBPS/xhtml/chapter1.xhtml`](test_data/real_epubs/heidegger_black_notebooks_VII_XI/OPS/xhtml/chapter1.xhtml) ("PONDERINGS VII" example)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files, CSS, images, and page template are in the `OPS/` directory, organized into `xhtml/`, `styles/`, and `images/` subdirectories.
*   Uses an NCX for ToC. An HTML ToC is also referenced in the OPF guide.
*   Chapters appear to be segmented into multiple XHTML files (e.g., `chapter1.xhtml`, `chapter1a.xhtml`, `chapter1b.xhtml`).
*   Endnotes seem to be collected at the end of chapter segments.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** "Ponderings VII–XI" (from OPF/NCX).
    *   **Major Section Titles (e.g., "PONDERINGS VII"):** `<h2>` with class `h2` and an `id` (e.g., `ch1`).

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`OEBPS/toc.ncx`):** Primary navigation. Flat structure (depth 1 in metadata, but `navLabel`s imply some hierarchy not represented by nesting). Links point to XHTML files, often with fragment identifiers (e.g., `xhtml/chapter1.xhtml#ch1`).
    *   **HTML ToC ([`OEBPS/xhtml/06_Contents.xhtml`](test_data/real_epubs/heidegger_black_notebooks_VII_XI/OPS/xhtml/06_Contents.xhtml)):** Referenced in the OPF `<guide>` section.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses endnotes, which appear to be linked to the end of chapter segments.
    *   **Reference Markup (in main text):** An empty `<a>` tag with an `id` (e.g., `id="rpg1fn1"`) immediately followed by a `<sup>` tag containing another `<a>` tag. This inner `<a>` tag links to an anchor in a *different* XHTML file, which seems to be a segment of the current chapter (e.g., `href="chapter1b.xhtml#pg1fn1"`). The link text is the note number. Example: `<a id="rpg1fn1"/><sup><a href="chapter1b.xhtml#pg1fn1">1</a></sup>`.
    *   **Note Text Location:** The `href` attributes point to other files within the same chapter's segments (e.g., `chapter1b.xhtml` for notes from `chapter1.xhtml`). This suggests notes are collected at the end of the last segment of each major "Pondering."

4.  **Emphasis:**
    *   Italics: `<em>` tags.

5.  **Page Number Markers:**
    *   Embedded as empty `<a>` tags with an `id` like `page_X` (e.g., `<a id="page_1"/>`).

6.  **Embedded Fonts:**
    *   No embedded fonts are listed in the OPF manifest.

7.  **Other Notable Features:**
    *   Use of Adobe page template (`styles/page-template.xpgt`).
    *   `Adept.expected.resource` meta tag in content files.
    *   Paragraphs use classes `noindents1` and `indents`.
    *   Internal cross-references also use the same complex anchor-plus-superscripted-link structure as footnotes.

**Summary for "Ponderings VII–XI (Black Notebooks)":**
This EPUB 2.0 uses `<h2>` for major section titles. A notable feature is the segmentation of chapters into multiple files (e.g., `chapter1.xhtml`, `chapter1a.xhtml`, `chapter1b.xhtml`). Endnotes are hyperlinked but point to anchors within these subsequent segment files, suggesting notes are collected at the end of a full "Pondering" section. The NCX is flat but `navLabel`s provide some hierarchical clues.
## 26. Martin Heidegger - Introduction to Metaphysics

**Source Directory:** [`test_data/real_epubs/heidegger_introduction_to_metaphysics/`](test_data/real_epubs/heidegger_introduction_to_metaphysics/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`content.opf`](test_data/real_epubs/heidegger_introduction_to_metaphysics/content.opf)
*   [`toc.ncx`](test_data/real_epubs/heidegger_introduction_to_metaphysics/toc.ncx)
*   [`text/part0010.html`](test_data/real_epubs/heidegger_introduction_to_metaphysics/text/part0010.html) (Chapter 1 example)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files (`partXXXX.html`, `titlepage.xhtml`) are in a `text/` subdirectory. CSS and images are in their respective subdirectories.
*   Includes Calibre metadata.
*   Uses an NCX for ToC and an HTML ToC (referenced in OPF guide).
*   Footnotes are same-page and hyperlinked.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** "Introduction to Metaphysics" (from OPF/NCX).
    *   **Chapter Titles (in content files):** Composed of two `<p>` tags. The first (`<p class="c307a">`) contains the chapter number (e.g., "CHAPTER ONE"). The second (`<p class="c22">`) contains the chapter title text (e.g., "The Fundamental Question of Metaphysics").
    *   **Sub-section Headers (e.g., §1, §2):** The NCX links to anchors for these, but in the sampled `part0010.html`, these sub-section titles were not explicitly present as distinct header elements. They might be integrated into the start of paragraphs or appear in subsequent split files if the chapter is segmented (though `part0010.html` itself was not a split file).

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Hierarchical (depth 3), reflecting Chapters and sub-sections within them (e.g., "1. Being and Becoming"). `navPoint` elements have `class="chapter"`. Links point to `text/partXXXX.html` files, with sub-sections using fragment identifiers (e.g., `text/part0013.html#page_105`).
    *   **HTML ToC ([`text/part0003.html`](test_data/real_epubs/heidegger_introduction_to_metaphysics/text/part0003.html)):** Referenced in the OPF `<guide>` section.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses same-page footnotes.
    *   **Reference Markup (in main text):** `<sup>` tag with class `calibre4` containing an `<a>` tag. The `<a>` tag has an `id` (e.g., `id="id_48"`) and an `href` pointing to the note anchor within the same file (e.g., `href="part0010.html#id_49"`). The link text is the note number.
    *   **Note Text Location:** At the bottom of the same XHTML file. Each note is a `<p class="c15">`. The note text starts with `<a id="id_49" href="part0010.html#id_48" class="calibre2">1</a>. ` (linking back to the reference) followed by the note content.

4.  **Emphasis:**
    *   Italics: `<em class="calibre3">`.

5.  **Page Number Markers:**
    *   Embedded as empty `<a>` tags with an `id` like `page_X` and class `calibre2` or `calibre1` (e.g., `<a id="page_2" class="calibre2"></a>`).

6.  **Embedded Fonts:**
    *   No embedded fonts are listed in the OPF manifest.

7.  **Other Notable Features:**
    *   Bracketed numbers like `{1}`, `{2}` appear as centered paragraphs (`<p class="c14">`), possibly indicating original lecture sectioning or editor's marks.

**Summary for "Introduction to Metaphysics":**
This EPUB 2.0, processed by Calibre, uses styled `<p>` tags for main chapter headings. The NCX provides good hierarchical navigation to sub-sections using anchors. It features a well-implemented same-page footnote system with bidirectional hyperlinks.
## 27. Fredric Jameson - The Hegel Variations

**Source Directory:** [`test_data/real_epubs/jameson_the_hegel_variations/`](test_data/real_epubs/jameson_the_hegel_variations/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`Jame_9781844678150_epub_opf_r1.opf`](test_data/real_epubs/jameson_the_hegel_variations/Jame_9781844678150_epub_opf_r1.opf)
*   [`OEBPS/Jame_9781844678150_epub_nav_r1.xhtml`](test_data/real_epubs/jameson_the_hegel_variations/OEBPS/Jame_9781844678150_epub_nav_r1.xhtml) (EPUB 3 Nav Doc)
*   [`OEBPS/Jame_9781844678150_epub_c01_r1.htm`](test_data/real_epubs/jameson_the_hegel_variations/OEBPS/Jame_9781844678150_epub_c01_r1.htm) (Chapter 1 example)

**Overall Structure:**
*   EPUB 3.0 format.
*   OPF and NCX files are in the root directory. Content XHTML, CSS, images, and fonts are in the `OEBPS/` directory.
*   Filenames within `OEBPS/` are prefixed (e.g., `Jame_9781844678150_epub_`).
*   Includes embedded TTF fonts (CharisSIL variants).
*   Uses an EPUB 3 Navigation Document (`Jame_9781844678150_epub_nav_r1.xhtml`) and an NCX for backward compatibility.
*   Footnotes are same-page and hyperlinked.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** "The Hegel Variations" (from OPF &amp; Nav Doc).
    *   **Chapter Number (in content files):** `<h1>` with class `chapter` and an `id` (e.g., `c01`). Contains the text "Chapter X".
    *   **Chapter Title (in content files):** A separate `<h1>` with class `chapter_title` (e.g., "Closure").

2.  **Table of Contents (ToC):**
    *   **EPUB 3 Nav Doc ([`OEBPS/Jame_9781844678150_epub_nav_r1.xhtml`](test_data/real_epubs/jameson_the_hegel_variations/OEBPS/Jame_9781844678150_epub_nav_r1.xhtml)):** Primary navigation.
        *   `epub:type="toc"`: Flat `<ol>` structure linking to XHTML files without fragment identifiers.
        *   `epub:type="landmarks"`: Includes cover, title page, ToC (HTML), and bodymatter (start of Chapter 1).
        *   `epub:type="page-list"`: Detailed list of page numbers linking to anchors within content files (e.g., `#pg1`).
    *   **NCX ToC (`Jame_9781844678150_epub_ncx_r1.ncx`):** Present for backward compatibility. (Structure not detailed here but assumed to mirror Nav Doc ToC).
    *   **HTML ToC ([`OEBPS/Jame_9781844678150_epub_toc_r1.htm`](test_data/real_epubs/jameson_the_hegel_variations/OEBPS/Jame_9781844678150_epub_toc_r1.htm)):** Referenced in the OPF `<guide>` and Nav Doc landmarks.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses same-page footnotes.
    *   **Reference Markup (in main text):** `<a>` tag with class `hlink`, an `id` (e.g., `c01-ftn1a`), and an `href` pointing to the note anchor within the same file (e.g., `#c01-ftn1`). The link text is a superscripted number within `<sup class="frac">`.
    *   **Note Text Location:** At the bottom of the same XHTML file, within a `<div class="footnote">`. Each note is a `<p class="footnote" id="c01-ftn1">`. The note text starts with `<a class="hlink" href="...#c01-ftn1a"><sup class="frac">1</sup></a>` (linking back to the reference) followed by the note content.
    *   An ornamental image (`images/Jame_9781844678150_epub_L02_r1.jpg`) separates main text from footnotes.

4.  **Emphasis:**
    *   Italics: `<i>` tags.

5.  **Page Number Markers:**
    *   EPUB 3 style: `<span epub:type="pagebreak" id="pgX" title="X"/>` within an `<a>` tag (e.g., `<a id="page1"><span epub:type="pagebreak" id="pg1" title="1"/></a>`). These correspond to the Nav Doc `page-list`.

6.  **Embedded Fonts:**
    *   TTF font files (CharisSIL variants) are listed in the OPF manifest and located in `OEBPS/fonts/`.

7.  **Other Notable Features:**
    *   `Adept.expected.resource` meta tag in content files.
    *   Paragraphs use classes `nonindent` and `indent`.

**Summary for "The Hegel Variations":**
This is a well-structured EPUB 3.0. It uses standard HTML headers for chapters and a robust, hyperlinked same-page footnote system. The EPUB 3 Navigation Document is comprehensive, including ToC, landmarks, and a page list. The EPUB embeds fonts.
## 28. Martin Heidegger - Ponderings VII–XI (Black Notebooks)

**Source Directory:** [`test_data/real_epubs/heidegger_black_notebooks_VII_XI/`](test_data/real_epubs/heidegger_black_notebooks_VII_XI/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`OEBPS/9780253025036.opf`](test_data/real_epubs/heidegger_black_notebooks_VII_XI/OPS/9780253025036.opf)
*   [`OEBPS/toc.ncx`](test_data/real_epubs/heidegger_black_notebooks_VII_XI/OPS/toc.ncx)
*   [`OEBPS/xhtml/chapter1.xhtml`](test_data/real_epubs/heidegger_black_notebooks_VII_XI/OPS/xhtml/chapter1.xhtml) ("PONDERINGS VII" example)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files, CSS, images, and page template are in the `OPS/` directory, organized into `xhtml/`, `styles/`, and `images/` subdirectories.
*   Uses an NCX for ToC. An HTML ToC is also referenced in the OPF guide.
*   Chapters appear to be segmented into multiple XHTML files (e.g., `chapter1.xhtml`, `chapter1a.xhtml`, `chapter1b.xhtml`).
*   Endnotes seem to be collected at the end of chapter segments.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** "Ponderings VII–XI" (from OPF/NCX).
    *   **Major Section Titles (e.g., "PONDERINGS VII"):** `<h2>` with class `h2` and an `id` (e.g., `ch1`).

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`OEBPS/toc.ncx`):** Primary navigation. Flat structure (depth 1 in metadata, but `navLabel`s imply some hierarchy not represented by nesting). Links point to XHTML files, often with fragment identifiers (e.g., `xhtml/chapter1.xhtml#ch1`).
    *   **HTML ToC ([`OEBPS/xhtml/06_Contents.xhtml`](test_data/real_epubs/heidegger_black_notebooks_VII_XI/OPS/xhtml/06_Contents.xhtml)):** Referenced in the OPF `<guide>` section.
    *   **Page List:** A comprehensive `<pageList>` is present in the NCX.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses endnotes, which appear to be linked to the end of chapter segments.
    *   **Reference Markup (in main text):** An empty `<a>` tag with an `id` (e.g., `id="rpg1fn1"`) immediately followed by a `<sup>` tag containing another `<a>` tag. This inner `<a>` tag links to an anchor in a *different* XHTML file, which seems to be a segment of the current chapter (e.g., `href="chapter1b.xhtml#pg1fn1"`). The link text is the note number.
    *   **Note Text Location:** Notes for a "Pondering" section appear to be collected at the end of the last segment of that section (e.g., notes for Pondering VII, which starts in `chapter1.xhtml`, are likely in `chapter1b.xhtml` or a subsequent segment).

4.  **Emphasis:**
    *   Italics: `<em>` tags.

5.  **Page Number Markers:**
    *   Embedded as empty `<a>` tags with an `id` like `page_X`. These correspond to the NCX `pageList`.

6.  **Embedded Fonts:**
    *   No embedded fonts are listed in the OPF manifest.

7.  **Other Notable Features:**
    *   Use of Adobe page template (`styles/page-template.xpgt`).
    *   `Adept.expected.resource` meta tag in content files.
    *   Paragraphs use classes `noindents1` and `indents`.
    *   Internal cross-references also use the same complex anchor-plus-superscripted-link structure as footnotes.

**Summary for "Ponderings VII–XI (Black Notebooks)":**
This EPUB 2.0 uses `<h2>` for major section titles. A notable feature is the segmentation of chapters into multiple files (e.g., `chapter1.xhtml`, `chapter1a.xhtml`, `chapter1b.xhtml`). Endnotes are hyperlinked but point to anchors within these subsequent segment files, suggesting notes are collected at the end of a full "Pondering" section. The NCX includes a detailed page list.
## 29. Eran Kaplan - Beyond Post-Zionism

**Source Directory:** [`test_data/real_epubs/kaplan_beyond_post_zionism/`](test_data/real_epubs/kaplan_beyond_post_zionism/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`content.opf`](test_data/real_epubs/kaplan_beyond_post_zionism/content.opf)
*   [`toc.ncx`](test_data/real_epubs/kaplan_beyond_post_zionism/toc.ncx)
*   [`Text/08_chapter01.xhtml`](test_data/real_epubs/kaplan_beyond_post_zionism/Text/08_chapter01.xhtml) (Chapter 1 example)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files are in a `Text/` subdirectory, images in `Images/`.
*   Includes Calibre metadata.
*   Uses an NCX for ToC and an HTML ToC (referenced in NCX and spine).
*   Endnotes are collected in a separate file.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** "Beyond Post-Zionism" (from OPF/NCX).
    *   **Chapter Number (in content files):** `<div class="chapter-number">ONE</div>`.
    *   **Chapter Title (in content files):** `<div class="chapter-title">POST-ZIONISM IN HISTORY</div>`.
    *   **Sub-heading:** `<div class="h">THE POST-ZIONIST CONDITION</div>`.
    *   Headers are styled `<div>` elements, not standard `<h1>-<h6>` tags.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Flat structure (depth 2 in metadata, but `navMap` is flat). `navPoint` elements have `class="chapter"`. Links point directly to XHTML files in `Text/` without fragment identifiers.
    *   **HTML ToC ([`Text/05_contents.xhtml`](test_data/real_epubs/kaplan_beyond_post_zionism/Text/05_contents.xhtml)):** Referenced in the NCX.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses endnotes.
    *   **Reference Markup (in main text):** `<sup>` tag with class `item2` containing an `<a>` tag. The `<a>` tag has an `id` (e.g., `ch01fn_1`) and an `href` pointing to an anchor in the notes file (`14_notes.xhtml#ch01fn1`). The link text is the note number.
    *   **Note Text Location:** All endnotes are collected in a dedicated HTML file, [`Text/14_notes.xhtml`](test_data/real_epubs/kaplan_beyond_post_zionism/Text/14_notes.xhtml), as indicated by the NCX "Notes" entry and `href` attributes.

4.  **Emphasis:**
    *   Italics: `<i class="calibre6">`.

5.  **Page Number Markers:**
    *   Embedded as empty `<a>` tags with an `id` like `page_XX` and class `item1` or `item`.

6.  **Embedded Fonts:**
    *   No embedded fonts are listed in the OPF manifest.

7.  **Other Notable Features:**
    *   Paragraphs are `<div>` elements with classes like `noindent-1st`, `indent`, `epigraph1`, `epipara`, `block`, `block1`.
    *   Use of an ornamental image (`<div class="lineimage"><img ... /></div>`).

**Summary for "Beyond Post-Zionism":**
This EPUB 2.0, likely Calibre-processed, uses `<div>` elements for headers and paragraphs. It features a hyperlinked endnote system with notes in a separate file. The NCX provides a flat navigation structure.
---
## 30. Levinas - Totality and Infinity

**Source Directory:** [`test_data/real_epubs/levinas_totality_and_infinity/`](test_data/real_epubs/levinas_totality_and_infinity/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`content.opf`](test_data/real_epubs/levinas_totality_and_infinity/content.opf)
*   [`toc.ncx`](test_data/real_epubs/levinas_totality_and_infinity/toc.ncx)
*   [`text/part0009_split_001.html`](test_data/real_epubs/levinas_totality_and_infinity/text/part0009_split_001.html) (Content example from Section I)
*   [`text/part0007.html`](test_data/real_epubs/levinas_totality_and_infinity/text/part0007.html) (Preface content)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files are segmented into `partXXXX.html` and `partXXXX_split_YYY.html` files within a `text/` subdirectory, typical of Calibre processing.
*   Includes Calibre metadata.
*   Standard image formats (`.jpeg`) in an `images/` directory.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Preface Title:** `<h1>` with class `chaptertitle` (e.g., in `text/part0007.html`).
    *   **Section Headers (e.g., "1. Desire for the Invisible"):** `<h2>` with class `heading1` (e.g., in `text/part0009_split_001.html`).

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Depth 4. Links to HTML files (often split) and specific internal anchors.
    *   **HTML ToC:** An HTML ToC is indicated in the OPF guide (`<reference type="toc" href="text/part0003.html#2RHM0-..." title="Contents"/>`) and in the NCX (`<navLabel><text>Table of Contents</text></navLabel><content src="text/part0003.html#..."/>`).

3.  **Footnotes/Endnotes:**
    *   **Dual System Observed:**
        *   **Endnotes (linking to other split files):** In `text/part0009_split_001.html`, references like `<span><a href="part0009_split_005.html#ftn1" ...>*</a></span>` and `<span><a href="part0009_split_005.html#ftn2" ...><sup ...>1</sup></a></span>` link to footnotes in a *different split file* within the same logical chapter/section. This suggests notes are collected at the end of larger, subsequently split, sections.
        *   **Same-page Footnotes (in Preface):** In `text/part0007.html` (Preface), references like `<span><a href="part0007.html#ftn2" ...>*</a></span>` and `<sup ...><span><a href="part0007.html#ftn3" ...>1</a></span></sup>` link to footnotes located at the bottom of the *same file* within a `<div class="footnotesection">`.
    *   **Note Markers:** Asterisks (`*`, `**`) and superscript numbers are used.
    *   **Note Text Structure (same-page):** `<div class="footnote" id="ftnX">` containing `<span class="footnotenumber">*</span>` or `<span class="footnotenumber1"><sup ...>N</sup></span>`, followed by note text in `<div class="calibre3"><div class="para2">...</div></div>`.

4.  **Citations/References (within note text):**
    *   Translator's notes are present (e.g., "We are translating 'étant' throughout by 'existent'...").
    *   Book/article titles typically italicized using `<span class="emphasistypeitalic">`.

5.  **Bibliography:**
    *   Not explicitly identified as a separate section in the examined files or NCX.

6.  **Page Number Markers:**
    *   Embedded using empty `<a>` tags with class `pcalibre pcalibre2 pcalibre1 calibre4` and an `id` like `pXX` (e.g., `<a id="p33" ...></a>` in `text/part0009_split_001.html`).

7.  **Emphasis:**
    *   Italics: `<span class="emphasistypeitalic">...</span>`.

**Summary for "Levinas - Totality and Infinity":**
This EPUB exhibits a mix of footnote handling: some sections appear to have endnotes collected at the end of logical (but split) chapters, while other sections (like the Preface) have traditional same-page footnotes. This dual behavior, combined with file splitting, presents a challenge for consistent note extraction. Header and paragraph structures are relatively standard with class-based styling.
---
## 31. Rorty - Philosophy and the Mirror of Nature

**Source Directory:** [`test_data/real_epubs/rorty_philosophy_and_the_mirror_of_nature/`](test_data/real_epubs/rorty_philosophy_and_the_mirror_of_nature/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`OEBPS/content.opf`](test_data/real_epubs/rorty_philosophy_and_the_mirror_of_nature/OEBPS/content.opf)
*   [`OEBPS/toc.ncx`](test_data/real_epubs/rorty_philosophy_and_the_mirror_of_nature/OEBPS/toc.ncx)
*   [`OEBPS/xhtml/12_Chapter01.xhtml`](test_data/real_epubs/rorty_philosophy_and_the_mirror_of_nature/OEBPS/xhtml/12_Chapter01.xhtml) (Chapter 1 content)
*   [`OEBPS/xhtml/09_Preface.xhtml`](test_data/real_epubs/rorty_philosophy_and_the_mirror_of_nature/OEBPS/xhtml/09_Preface.xhtml) (Preface content)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files are located within an `OEBPS/xhtml/` subdirectory.
*   Filenames are logically named (e.g., `01_Cover.xhtml`, `12_Chapter01.xhtml`).
*   Includes embedded `.ttf` fonts (CharisSIL, DejaVuSans).
*   Standard OPF/NCX structure.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Preface Title:** `<p class="fmtitle"><i>Preface</i></p>`.
    *   **Chapter Number:** `<p class="chno">CHAPTER N</p>`.
    *   **Chapter Title:** `<p class="chtitle">...</p>`.
    *   **Numbered Section Headers (within chapters):** `<p class="h1">N. S<small>ECTION</small> T<small>ITLE</small></p>`. Uses `<small>` for parts of the title.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Depth 3. Links to XHTML files and specific internal anchors (e.g., `xhtml/12_Chapter01.xhtml#ch1_1`).
    *   **HTML ToC (`xhtml/07_Contents.xhtml`):** Referenced in OPF guide.
    *   **Page List (`<pageList>` in NCX):** Present, mapping page numbers to anchors.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses same-page footnotes.
    *   **Reference Markup (in main text):** `<sup><a href="#rfnX_Y" id="fnX_Y">N</a></sup>` (e.g., `<sup><a href="#rfn1_1" id="fn1_1">1</a></sup>`).
    *   **Note Text Location:** At the bottom of the corresponding XHTML file. Each note starts with `<p class="foott">` or `<p class="foot">`, followed by the superscript reference link and then the note text (e.g., `<p class="foott"><sup><a href="#fn1_1" id="rfn1_1">1</a></sup> See Kant’s ...</p>`).

4.  **Citations/References (within note text):**
    *   Book/article titles typically italicized using `<i>`. Other publication details are plain text.

5.  **Bibliography/Index:**
    *   An "Index" is listed in the NCX, linking to `xhtml/24_Index01.xhtml`.
    *   No explicit "Bibliography" found in NCX, but back matter files like `xhtml/22_Bm01.xhtml` ("The Philosopher as Expert") and `xhtml/23_Bm02.xhtml` ("Afterword") exist.

6.  **Page Number Markers:**
    *   Embedded using `<a id="page_X"/>` or `<a id="page_romanX"/>`.

7.  **Emphasis:**
    *   Italics: `<i>...</i>`.
    *   Small caps: `<small>...</small>` (primarily in headers).

8.  **Images:**
    *   One content image (`images/img01.png`) is listed in the manifest and used in Chapter 1.

**Summary for "Rorty - Philosophy and the Mirror of Nature":**
This EPUB is well-structured with same-page footnotes and a clear NCX ToC that includes a page list. Headers are consistently styled using `<p>` tags with specific classes. The use of embedded fonts is noted. The structure is relatively straightforward for RAG processing.
---
## 32. Rosenzweig - The Star of Redemption

**Source Directory:** [`test_data/real_epubs/rosenzweig_the_star_of_redemption/`](test_data/real_epubs/rosenzweig_the_star_of_redemption/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`OEBPS/content.opf`](test_data/real_epubs/rosenzweig_the_star_of_redemption/OEBPS/content.opf)
*   [`OEBPS/toc.ncx`](test_data/real_epubs/rosenzweig_the_star_of_redemption/OEBPS/toc.ncx)
*   [`OEBPS/xhtml/09_P1_Introduction01.xhtml`](test_data/real_epubs/rosenzweig_the_star_of_redemption/OEBPS/xhtml/09_P1_Introduction01.xhtml) (Part 1 Introduction)
*   [`OEBPS/xhtml/10_P1_Chapter01.xhtml`](test_data/real_epubs/rosenzweig_the_star_of_redemption/OEBPS/xhtml/10_P1_Chapter01.xhtml) (Part 1, Book 1)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files are located within an `OEBPS/xhtml/` subdirectory.
*   Filenames are logically named (e.g., `01_Cover.xhtml`, `09_P1_Introduction01.xhtml`).
*   Includes embedded `FreeSerif` `.ttf` fonts.
*   Contains some full-page images (`pgX.jpg`) in the manifest, possibly diagrams or illustrative plates.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Part/Book/Introduction Titles:** Use `<p>` tags with classes like `cta` (e.g., `<p class="cta">...INTRODUCTION</p>`) and `ctc` (e.g., `<p class="ctc">...God and His Being<br/>or<br/>Metaphysics</p>`). These often contain `<a>` tags linking back to the HTML ToC.
    *   **Section Headers (within chapters/introductions):** Use `<p class="sec">` (e.g., `<p class="sec">Negative Theology</p>`) or `<p class="sec1">` (e.g., `<p class="sec1">THE TWO WAYS</p>`).

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Depth 2. Links to XHTML files.
    *   **HTML ToC (`xhtml/05_Contents.xhtml`):** Referenced in OPF guide.
    *   **Page List (`<pageList>` in NCX):** Present, mapping page numbers to anchors.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses same-page footnotes.
    *   **Reference Markup (in main text):** Simple superscript numbers, e.g., `<sup>1</sup>`, `<sup>2</sup>`. These are *not* wrapped in `<a>` tags in the examined content files.
    *   **Note Text Location:** At the bottom of the corresponding XHTML file. Each note starts with `<p class="ntnlf">` or `<p class="ntnl">` (e.g., `<p class="ntnlf"><sup>1</sup> Translator’s addition.</p>`).

4.  **Citations/References (within note text):**
    *   Translator's notes are explicitly marked.

5.  **Bibliography/Index:**
    *   "Indices" (Jewish Sources, Names, Subjects) are listed in the NCX, linking to `xhtml/26_Index.xhtml` and subsequent `Index0X.xhtml` files.
    *   No explicit "Bibliography" found in NCX.

6.  **Page Number Markers:**
    *   Embedded using `<a id="page_X"/>`.

7.  **Emphasis:**
    *   Italics: `<i>...</i>`.

8.  **Images:**
    *   The manifest lists `pg1.jpg`, `pg91.jpg`, `pg263.jpg`. Their exact nature (diagrams, plates) would require viewing.

**Summary for "Rosenzweig - The Star of Redemption":**
This EPUB uses a fairly clean structure with same-page footnotes referenced by simple superscript numbers. Headers are styled using `<p>` tags with specific classes. The NCX ToC is relatively flat but functional. The presence of full-page images might be relevant if they contain textual content.
---
## 33. Sartre - Being and Nothingness

**Source Directory:** [`test_data/real_epubs/sartre_being_and_nothingness/`](test_data/real_epubs/sartre_being_and_nothingness/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`9781982105464.opf`](test_data/real_epubs/sartre_being_and_nothingness/9781982105464.opf)
*   [`e9781982105464/xhtml/nav.xhtml`](test_data/real_epubs/sartre_being_and_nothingness/e9781982105464/xhtml/nav.xhtml) (EPUB 3 Navigation Document)
*   [`e9781982105464/xhtml/intro.xhtml`](test_data/real_epubs/sartre_being_and_nothingness/e9781982105464/xhtml/intro.xhtml) (Introduction content)
*   [`e9781982105464/xhtml/part01_ch01.xhtml`](test_data/real_epubs/sartre_being_and_nothingness/e9781982105464/xhtml/part01_ch01.xhtml) (Part 1, Chapter 1 content)

**Overall Structure:**
*   EPUB 3.0 format.
*   Content files are located within an `e9781982105464/xhtml/` subdirectory.
*   Filenames are logically named (e.g., `intro.xhtml`, `part01_ch01.xhtml`).
*   Includes embedded `.ttf` fonts (EBGaramond, Roboto).
*   Uses an EPUB 3 Navigation Document (`nav.xhtml`) and includes a `toc.ncx` for backward compatibility.
*   Contains extensive accessibility metadata.
*   A dedicated `footnotes.xhtml` file is present.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and in `nav.xhtml`.
    *   **Introduction Title:** `<h1>` with class `h1c` (e.g., `<h1 class="h1c" id="intro_hd">...INTRODUCTION...</h1>`). Contains nested `<sup>` and `<span>` for markers and subtitles.
    *   **Chapter Title/Number:** `<h2>` with class `h2ch` (e.g., `<h2 class="h2ch" id="part01_ch01_hd">...Chapter 1...THE ORIGIN OF NEGATION</span></h2>`). Contains nested `<span>` elements.
    *   **Section Headers (within chapters/introduction):** `<h2>` with class `h2a` (e.g., `<h2 class="h2a" id="intro_hd_lev01">I. THE IDEA OF THE PHENOMENON</h2>`) or `<h3>` with class `h3` (e.g., `<h3 class="h3" id="part01_ch01_lev01">I. QUESTIONING...</h3>`). These also include `<sup>` for footnote references.

2.  **Table of Contents (ToC):**
    *   **EPUB 3 Nav Doc (`nav.xhtml`):** Primary navigation. Uses nested `<ol>` and `<li>` for hierarchy. Links to XHTML files and specific internal anchors. Includes `epub:type` attributes for `toc`, `landmarks`, and `page-list`.
    *   **NCX ToC (`toc.ncx`):** Present for EPUB 2 compatibility.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses endnotes.
    *   **Reference Markup (in main text):** `<sup class="sup"><a href="footnotes.xhtml#fn_id" id="fn_ref_id">N</a></sup>` (e.g., `<sup class="sup"><a href="footnotes.xhtml#introfn1" id="introfn_1">1</a></sup>`).
    *   **Note Text Location:** All footnotes/endnotes are collected in the dedicated HTML file [`e9781982105464/xhtml/footnotes.xhtml`](test_data/real_epubs/sartre_being_and_nothingness/e9781982105464/xhtml/footnotes.xhtml), as indicated by the `href` attributes in the note references and its presence in the manifest/spine.

4.  **Citations/References (within note text):**
    *   (To be confirmed by examining `footnotes.xhtml`).

5.  **Bibliography/Index:**
    *   "Bibliography" is listed in `nav.xhtml`, linking to `bibliography.xhtml`.
    *   "Index" is listed in `nav.xhtml`, linking to `index.xhtml` (and `index01.xhtml` is also in manifest/spine).

6.  **Page Number Markers:**
    *   EPUB 3 style: `<span aria-label="page X" id="page_X" role="doc-pagebreak"/>`.

7.  **Emphasis:**
    *   Italics: `<i>...</i>`.

8.  **Other Notable Features:**
    *   Content sections are wrapped in `<section role="doc-introduction">` or `<section role="doc-chapter">`.
    *   Some headings include markers like `<sup class="sup2">GT9</sup>`, possibly publisher/editorial annotations.

**Summary for "Sartre - Being and Nothingness":**
This is a modern EPUB 3 file with good semantic markup, including a detailed navigation document with ToC, landmarks, and a page list. Endnotes are conveniently consolidated into a single `footnotes.xhtml` file. The structure is well-defined and should be relatively straightforward for RAG processing, with clear indicators for headers, page breaks, and notes.
---
## 34. Sennet - The Craftsman

**Source Directory:** [`test_data/real_epubs/sennet_the_craftsman/`](test_data/real_epubs/sennet_the_craftsman/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`content.opf`](test_data/real_epubs/sennet_the_craftsman/content.opf)
*   [`toc.ncx`](test_data/real_epubs/sennet_the_craftsman/toc.ncx)
*   [`text/part0007_split_000.html`](test_data/real_epubs/sennet_the_craftsman/text/part0007_split_000.html) (Part One / Chapter One Headers)
*   [`text/part0007_split_001.html`](test_data/real_epubs/sennet_the_craftsman/text/part0007_split_001.html) (Chapter 1 Content)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files are segmented into `partXXXX.html` and `partXXXX_split_YYY.html` files within a `text/` subdirectory, characteristic of Calibre processing.
*   Includes Calibre metadata.
*   Embedded `.ttf` fonts are present, and `META-INF/encryption.xml` suggests they may be obfuscated.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Part Title:** `<h1>` with class `title` (e.g., `<h1 class="title" id="cra0010006">...<span class="small">PART ONE</span>: Craftsman</h1>`).
    *   **Chapter Number (as a title):** `<h3>` with class `title5` (e.g., `<h3 class="title5" id="cra0000006">...CHAPTER ONE</h3>`).
    *   **Chapter Sub-Title (actual title):** `<h2>` with class `title6` (e.g., `<h2 class="title6" id="cra0000007">The Troubled Craftsman</h2>`).
    *   **Section Headers (within chapters):** `<h3>` with class `title3` (e.g., `<h3 class="title3" id="cra0000015">The Modern Hephaestus</h3>`), often followed by an italicized sub-header in `<h3>` with class `title4` (e.g., `<h3 class="title4" id="cra0000016"><span class="em">Ancient Weavers and Linux Programmers</span></h3>`).

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Depth 4. Links to HTML files (often split files).
    *   **HTML ToC:** `text/part0004.html` is listed in the NCX as "Contents".

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses endnotes.
    *   **Reference Markup (in main text):** `<a id="ch001fn1a"></a><a href="part0018.html#ch001fn1" class="hlink"><sup class="small3">1</sup></a>`. This consists of an empty anchor followed by a linked superscript number.
    *   **Note Text Location:** All notes are collected in a dedicated HTML file, [`text/part0018.html`](test_data/real_epubs/sennet_the_craftsman/text/part0018.html), as indicated by the `href` attributes and the NCX "Notes" entry.

4.  **Citations/References (within note text):**
    *   (To be confirmed by examining `text/part0018.html`).

5.  **Bibliography/Index:**
    *   "Index" is listed in the NCX, linking to `text/part0019.html`.
    *   No explicit "Bibliography" found in NCX.

6.  **Page Number Markers:**
    *   Embedded using `<a id="page_X"></a>`.

7.  **Emphasis:**
    *   Italics: `<span class="em">...</span>`.

8.  **Images:**
    *   Content images are present (e.g., `<img src="../images/00006.jpeg" ... />`).

**Summary for "Sennet - The Craftsman":**
This EPUB, likely processed by Calibre, features extensive file splitting. It uses an endnote system with all notes collected in a separate file. Headers have a multi-level structure using `<h1>`, `<h2>`, and `<h3>` with various classes. Embedded fonts are present and potentially obfuscated.
---
## 35. The Descartes Dictionary

**Source Directory:** [`test_data/real_epubs/the_descartes_dictionary/`](test_data/real_epubs/the_descartes_dictionary/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`OEBPS/9781472507266.opf`](test_data/real_epubs/the_descartes_dictionary/OEBPS/9781472507266.opf)
*   [`OEBPS/toc.ncx`](test_data/real_epubs/the_descartes_dictionary/OEBPS/toc.ncx)
*   [`OEBPS/html/9781472514691_Int.html`](test_data/real_epubs/the_descartes_dictionary/OEBPS/html/9781472514691_Int.html) (Introduction)
*   [`OEBPS/html/9781472514691_Ch01.html`](test_data/real_epubs/the_descartes_dictionary/OEBPS/html/9781472514691_Ch01.html) (Dictionary Entries "Terms and names")

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files are located within an `OEBPS/html/` subdirectory.
*   Filenames include an ISBN-like prefix (e.g., `9781472514691_FM.html`).
*   No embedded fonts are declared in the OPF.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Main Section Titles (e.g., "Introduction", "Terms and names"):** `<p class="ChapTitle">...<a href="...">Title</a></p>`.
    *   **Sub-Section Headers (e.g., "A sketch of Descartes’s life"):** `<p class="AHead"><strong>Title</strong></p>`.
    *   **Further Sub-Headers (e.g., "Descartes’s metaphysics: The roots"):** `<p class="BHead"><strong><em>Title</em></strong></p>`.
    *   **Dictionary Entry Term:** `<p class="Text1"><strong>Term</strong>. ...</p>`.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Depth effectively 2. Links to XHTML files and specific internal anchors.
    *   **HTML ToC:** Located within `html/9781472514691_FM.html#toc` as per OPF guide.

3.  **Footnotes/Endnotes:**
    *   **Type:** No footnote/endnote references were observed in the sample content files (`_Int.html`, `_Ch01.html`). The OPF manifest does not list a dedicated notes file, suggesting this dictionary might not use them extensively, or they are integrated differently.

4.  **Citations/References:**
    *   Internal cross-references to other dictionary entries are bolded within the text (e.g., "For more, see <strong><em>Distinction</em></strong>, <strong><em>Real</em></strong>").
    *   Bibliographic references within the text use parenthetical citations (e.g., "(AT VII 41; CSM II 28)").

5.  **Bibliography:**
    *   A "Bibliography" section is linked in the NCX, pointing to `html/9781472514691_Bib.html#bib1`.

6.  **Page Number Markers:**
    *   Embedded using `<a id="page_X"/>`.

7.  **Emphasis:**
    *   Italics: `<em>...</em>`.
    *   Bold: `<strong>...</strong>`.

**Summary for "The Descartes Dictionary":**
This dictionary-style EPUB has a clear structure based on alphabetical entries. Headers are styled using `<p>` tags with specific classes. It appears to rely on in-text citations and a dedicated bibliography section rather than footnotes/endnotes for references, which simplifies one aspect of RAG processing. The NCX provides straightforward navigation to main sections.
---
## 36. The Husserl Dictionary

**Source Directory:** [`test_data/real_epubs/the_husserl_dictionary/`](test_data/real_epubs/the_husserl_dictionary/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`content.opf`](test_data/real_epubs/the_husserl_dictionary/content.opf) (Located in EPUB root)
*   [`toc.ncx`](test_data/real_epubs/the_husserl_dictionary/toc.ncx) (Located in EPUB root)
*   [`text/part0005.html`](test_data/real_epubs/the_husserl_dictionary/text/part0005.html) (Introduction)
*   [`text/part0008_split_000.html`](test_data/real_epubs/the_husserl_dictionary/text/part0008_split_000.html) (Dictionary A-Z Start)

**Overall Structure:**
*   EPUB 2.0 format.
*   `content.opf` and `toc.ncx` are in the EPUB root directory.
*   Content XHTML files are in a `text/` subdirectory. Some content files are split (e.g., `part0008_split_XXX.html`), likely due to Calibre processing.
*   Includes Calibre metadata.
*   No embedded fonts listed in OPF.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Main Section Titles (e.g., "Introduction", "The Husserl Dictionary A-Z"):** `<h1>` with classes like `toc-t` or `ack`. Often contain `<a>` tags linking to the HTML ToC.
    *   **Alphabetical Section Header (e.g., "— A —"):** `<h1>` with class `cn` and nested `<strong>`.
    *   **Dictionary Entry Term:** `<p class="also1a"><strong class="calibre2">Term (<em class="calibre3">German Term</em>)</strong>...</p>` or `<p class="noindent"><strong class="calibre2">Term (<em class="calibre3">German Term</em>)</strong>...</p>`. The term is bold, German equivalent in italics. "See also" cross-references follow in bold.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Depth 2. Links to XHTML files in `text/` and some specific anchors (e.g., for bibliography sub-sections).
    *   **HTML ToC:** Located at `text/part0003.html` as per OPF guide.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses same-page footnotes.
    *   **Reference Markup (in Introduction):** `<a id="int1-1" href="part0005.html#int1_1" class="calibre1"><sup class="calibre12">1</sup></a>`.
    *   **Note Text Location (in Introduction):** At the bottom of `text/part0005.html`, starting with `<p class="note">` or `<p class="note1">`, followed by the linked reference.
    *   **Note References (in Dictionary Entries):** No footnote/endnote references were observed in the sample dictionary entry file (`text/part0008_split_000.html`).

4.  **Citations/References:**
    *   Internal cross-references to other dictionary entries are bolded (e.g., `<strong class="calibre2">consciousness</strong>`).
    *   Bibliographic references within text use italics for titles and sometimes link to a bibliography section (e.g., `(<em class="calibre3">Ideas</em> I § 76)` or `<a id="bib_33" href="part0009.html#bib-33" class="calibre1"><strong class="calibre2"><em class="calibre3">The Idea of Phenomenology</em></strong></a>`).

5.  **Bibliography/Index:**
    *   "Bibliography" and "Index" sections are listed in the NCX, linking to `text/part0009.html` and `text/part0010_split_000.html` respectively. The bibliography has sub-sections navigable via the NCX.

6.  **Page Number Markers:**
    *   Embedded using `<a id="pageX" class="calibre1"></a>`.

7.  **Emphasis:**
    *   Italics for German terms or book titles: `<em class="calibre3">...</em>`.
    *   Bold for entry terms and cross-references: `<strong class="calibre2">...</strong>`.

**Summary for "The Husserl Dictionary":**
This dictionary-style EPUB, likely Calibre-processed, uses same-page footnotes in introductory sections. Dictionary entries themselves rely on bolded cross-references and italicized terms. The NCX ToC is relatively flat but provides access to main sections and bibliography sub-sections.
---
## 37. Gadamer - Truth and Method

**Source Directory:** [`test_data/real_epubs/truth_and_method/`](test_data/real_epubs/truth_and_method/)

**Date Analyzed:** 2025-05-09

**Key Files Examined:**
*   [`OEBPS/content.opf`](test_data/real_epubs/truth_and_method/OEBPS/content.opf)
*   [`OEBPS/toc.ncx`](test_data/real_epubs/truth_and_method/OEBPS/toc.ncx)
*   [`OEBPS/intro.html`](test_data/real_epubs/truth_and_method/OEBPS/intro.html) (Introduction)
*   [`OEBPS/ch1.html`](test_data/real_epubs/truth_and_method/OEBPS/ch1.html) (Chapter 1)

**Overall Structure:**
*   EPUB 2.0 format.
*   Content files are located directly within the `OEBPS/` directory.
*   Filenames are logical (e.g., `intro.html`, `ch1.html`, `ch1a.html`). The `a` suffix (e.g., `ch1a.html`) likely indicates a continuation or a notes section for the preceding file.
*   No embedded fonts listed in OPF.

**Formatting Patterns:**

1.  **Titles & Headers:**
    *   **Book Title:** Defined in `<dc:title>` (OPF) and `<docTitle>` (NCX).
    *   **Introduction Title:** `<p class="fmt">...<a href="contents.html#re_intro" id="int">Introduction</a></p>`.
    *   **Chapter Number:** `<p class="cn">...<a href="contents.html#re_ch1" id="ch1">Chapter 1</a></p>`.
    *   **Chapter Title:** `<p class="ct">...<a href="contents.html#re_ch1">Transcending the Aesthetic Dimension</a></p>`.
    *   **Section Headers (within chapters):** `<p class="h1" id="ch1-sec1">...Title...</p>`.
    *   **Sub-Section Headers:** `<p class="h2a">Title</p>` or `<p class="h3">Title</p>`.

2.  **Table of Contents (ToC):**
    *   **NCX ToC (`toc.ncx`):** Primary navigation. Effective depth appears to be 3 or more due to nested sections. Links to XHTML files and specific internal anchors.
    *   **HTML ToC (`contents.html`):** Referenced in OPF guide.

3.  **Footnotes/Endnotes:**
    *   **Type:** Uses endnotes, likely collected in separate files (e.g., `ch1a.html` for notes from `ch1.html`).
    *   **Reference Markup (in main text):** `<a href="ch1a.html#fn1-ref" id="fn1"><sup>1</sup></a>`. This is a superscript number within an `<a>` tag, linking to a different HTML file (e.g., `ch1a.html`) and a specific anchor.
    *   **Note Text Location:** Assumed to be in the linked `chXa.html` files. (Content of these note files not examined in this step).

4.  **Citations/References (within note text):**
    *   (To be confirmed by examining note files like `ch1a.html`).

5.  **Bibliography/Index:**
    *   "Subject Index" and "Author Index" are listed in the NCX, linking to `subject_index.html` and `author_index.html` respectively.
    *   No explicit "Bibliography" found in NCX, but "Appendices" and "Supplements" are listed, which might contain bibliographic information.

6.  **Page Number Markers:**
    *   Embedded using `<a id="pX"/>` or `<a id="pxX"/>`.

7.  **Emphasis:**
    *   Italics: `<span class="italic">...</span>`.

**Summary for "Gadamer - Truth and Method":**
This EPUB uses a system where notes for a chapter (e.g., `ch1.html`) appear to be collected in a corresponding `ch1a.html` file. Headers are styled using `<p>` tags with various classes. The NCX ToC is detailed, reflecting the book's structure.