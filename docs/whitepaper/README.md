# Building the GeoTask White Paper

The canonical source is:

```text
GeoTask_White_Paper_v0.1.md
```

Keep the Markdown file authoritative. Generated HTML, DOCX, and PDF files should identify the source commit used to build them.

## HTML

```bash
pandoc docs/whitepaper/GeoTask_White_Paper_v0.1.md \
  --standalone \
  --toc \
  --metadata title="GeoTask White Paper v0.1" \
  -o GeoTask_White_Paper_v0.1.html
```

## DOCX

```bash
pandoc docs/whitepaper/GeoTask_White_Paper_v0.1.md \
  --standalone \
  --toc \
  --metadata title="GeoTask White Paper v0.1" \
  -o GeoTask_White_Paper_v0.1.docx
```

## PDF

Pandoc requires an installed PDF engine. For Chinese text, XeLaTeX is recommended:

```bash
pandoc docs/whitepaper/GeoTask_White_Paper_v0.1.md \
  --standalone \
  --toc \
  --pdf-engine=xelatex \
  -V CJKmainfont="Noto Sans CJK SC" \
  -V geometry:margin=22mm \
  -o GeoTask_White_Paper_v0.1.pdf
```

The font name is an example. Use a legally installed CJK font available on the build machine. Do not commit or redistribute font files.

## Release Practice

1. validate documentation tests;
2. build from a clean Git commit;
3. record the commit hash in release notes;
4. inspect headings, tables, code blocks, links, and CJK line breaks;
5. publish generated documents as release assets when possible rather than treating binaries as the canonical source.

Run documentation tests:

```bash
pytest tests/test_documentation_system.py -q
```
