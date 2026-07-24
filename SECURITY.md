# Security Policy

## Supported versions

Only the latest released version receives security fixes.

| Version | Supported |
|---------|-----------|
| latest  | ✅        |
| older   | ❌        |

## Reporting a vulnerability

Please report security issues privately via
[GitHub Security Advisories](https://github.com/loganrooks/audiobookify/security/advisories/new)
rather than opening a public issue.

Expect an initial response within 7 days.

## Security considerations for users

Audiobookify processes untrusted input and shells out to external tools. Things
worth knowing:

- **Ebook files are untrusted input.** EPUB files are ZIP archives containing
  XML and HTML that are parsed with `lxml`, `BeautifulSoup`, and `ebooklib`.
  Only convert files you obtained from a source you trust.
- **Text is sent to Microsoft.** Edge TTS is a cloud service. The full text of
  every book you convert is transmitted to Microsoft's speech endpoint. Do not
  use this tool for confidential material.
- **`--pronunciation` and `--voice-mapping` read local config files.** These are
  parsed as JSON or key/value text and applied as string substitutions. Treat
  them like any other config file: don't run ones you didn't write.
- **FFmpeg is invoked as a subprocess.** Audiobookify passes argument lists
  (never `shell=True`), but a vulnerable FFmpeg build is still a risk surface.
  Keep FFmpeg up to date.
- **DRM.** Audiobookify does not remove or circumvent DRM. Input files must
  already be DRM-free.
