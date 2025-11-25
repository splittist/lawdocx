"""Helpers for building DOCX fixtures on the fly without storing binaries."""
from __future__ import annotations

import textwrap
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
RELATIONSHIP_NAMESPACE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
W14_NAMESPACE = "http://schemas.microsoft.com/office/word/2010/wordml"
W15_NAMESPACE = "http://schemas.microsoft.com/office/word/2012/wordml"

CORE_XML = textwrap.dedent(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
      <dc:title>Sample Title</dc:title>
      <dc:creator>Author Name</dc:creator>
      <cp:lastModifiedBy>Reviewer</cp:lastModifiedBy>
      <cp:revision>5</cp:revision>
    </cp:coreProperties>
    """
).strip()


APP_XML = textwrap.dedent(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
      <Template>Normal.dotm</Template>
      <Company>Example Co</Company>
    </Properties>
    """
).strip()


CUSTOM_XML = textwrap.dedent(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
      <property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="2" name="CustomNote">
        <vt:lpwstr>Sample value</vt:lpwstr>
      </property>
      <property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="3" name="CustomNumber">
        <vt:i4>123</vt:i4>
      </property>
    </Properties>
    """
).strip()


def _wrap_paragraphs(paragraphs: list[str]) -> str:
    xml_paragraphs = []
    for text in paragraphs:
        escaped = escape(text)
        xml_paragraphs.append(
            textwrap.dedent(
                f"""
                <w:p xmlns:w=\"{WORD_NAMESPACE}\">\n      <w:r><w:t>{escaped}</w:t></w:r>\n    </w:p>
                """
            ).strip()
        )
    return "\n".join(xml_paragraphs)


DOCUMENT_XML = textwrap.dedent(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:body>
        <w:p>
          <w:r>
            <w:t>Hello</w:t>
          </w:r>
        </w:p>
      </w:body>
    </w:document>
    """
).strip()

HEADER_XML = textwrap.dedent(
    f"""
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:hdr xmlns:w="{WORD_NAMESPACE}" xmlns:r="{RELATIONSHIP_NAMESPACE}">
      <w:p><w:r><w:t>{{header_text}}</w:t></w:r></w:p>
    </w:hdr>
    """
).strip()


FOOTER_XML = textwrap.dedent(
    f"""
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:ftr xmlns:w="{WORD_NAMESPACE}" xmlns:r="{RELATIONSHIP_NAMESPACE}">
      <w:p><w:r><w:t>{{footer_text}}</w:t></w:r></w:p>
    </w:ftr>
    """
).strip()


EMPTY_RELS_XML = (
    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
    "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"/>"
)


DOCUMENT_RELS_WITH_CUSTOM_XML = textwrap.dedent(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId10" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXml" Target="../customXml/item1.xml"/>
      <Relationship Id="rId11" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXml" Target="../customXml/item2.xml"/>
    </Relationships>
    """
).strip()


CUSTOM_XML_ITEM_ONE = textwrap.dedent(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <root>
      <entry>Custom XML payload one</entry>
    </root>
    """
).strip()


CUSTOM_XML_ITEM_TWO = textwrap.dedent(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <root>
      <entry>Custom XML payload two</entry>
    </root>
    """
).strip()


RELATIONSHIPS_XML = textwrap.dedent(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
      <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
      <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties" Target="docProps/custom.xml"/>
    </Relationships>
    """
).strip()


RELATIONSHIPS_XML_NO_CUSTOM = textwrap.dedent(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
      <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
    </Relationships>
    """
).strip()


RELATIONSHIPS_WITH_DOCUMENT = textwrap.dedent(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
    </Relationships>
    """
).strip()

CONTENT_TYPES_WITH_STYLES = textwrap.dedent(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
      <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
      <Default Extension="xml" ContentType="application/xml"/>
      <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
      <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
    </Types>
    """
).strip()

STYLES_XML = textwrap.dedent(
    f"""
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:styles xmlns:w="{WORD_NAMESPACE}">
      <w:style w:type="paragraph" w:styleId="Heading1">
        <w:name w:val="Heading 1"/>
      </w:style>
      <w:style w:type="paragraph" w:styleId="BodyText">
        <w:name w:val="Body Text"/>
      </w:style>
      <w:style w:type="paragraph" w:styleId="ArticleTitle">
        <w:name w:val="Article Heading"/>
      </w:style>
    </w:styles>
    """
).strip()

DOCUMENT_RELS_WITH_NOTES = textwrap.dedent(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/>
      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/endnotes" Target="endnotes.xml"/>
    </Relationships>
    """
).strip()


DOCUMENT_RELS_WITH_HEADER_FOOTER = textwrap.dedent(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
    </Relationships>
    """
).strip()

DOCUMENT_RELS_WITH_CHANGES = textwrap.dedent(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
      <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/>
      <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/endnotes" Target="endnotes.xml"/>
    </Relationships>
    """
).strip()


def _content_types_xml(include_custom: bool) -> str:
    overrides = [
        "  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>",
        "  <Override PartName=\"/docProps/core.xml\" ContentType=\"application/vnd.openxmlformats-package.core-properties+xml\"/>",
        "  <Override PartName=\"/docProps/app.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.extended-properties+xml\"/>",
    ]
    if include_custom:
        overrides.append(
            "  <Override PartName=\"/docProps/custom.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.custom-properties+xml\"/>"
        )

    override_str = "\n".join(overrides)
    return textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
        {override_str}
        </Types>
        """
    ).strip()


def _content_types_with_header_footer(paragraphs: list[str]) -> str:
    overrides = [
        "  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>",
        "  <Override PartName=\"/word/header1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml\"/>",
        "  <Override PartName=\"/word/footer1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml\"/>",
    ]
    return textwrap.dedent(
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
        {override_str}
        </Types>
        """
    ).strip().format(override_str="\n".join(overrides))


def _content_types_with_notes() -> str:
    overrides = [
        "  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>",
        "  <Override PartName=\"/word/footnotes.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml\"/>",
        "  <Override PartName=\"/word/endnotes.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml\"/>",
    ]
    return textwrap.dedent(
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
        {override_str}
        </Types>
        """
    ).strip().format(override_str="\n".join(overrides))


def _content_types_for_changes() -> str:
    overrides = [
        "  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>",
        "  <Override PartName=\"/word/header1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml\"/>",
        "  <Override PartName=\"/word/footer1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml\"/>",
        "  <Override PartName=\"/word/footnotes.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml\"/>",
        "  <Override PartName=\"/word/endnotes.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml\"/>",
    ]

    return textwrap.dedent(
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
        {override_str}
        </Types>
        """
    ).strip().format(override_str="\n".join(overrides))


def _content_types_with_comments() -> str:
    overrides = [
        "  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>",
        "  <Override PartName=\"/word/comments.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml\"/>",
        "  <Override PartName=\"/word/commentsExtended.xml\" ContentType=\"application/vnd.ms-word.commentsExtended+xml\"/>",
    ]

    return textwrap.dedent(
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
        {override_str}
        </Types>
        """
    ).strip().format(override_str="\n".join(overrides))


def create_metadata_docx(
    base_dir: Path,
    name: str,
    *,
    include_custom: bool = True,
    include_custom_xml: bool = True,
) -> Path:
    """Create a minimal DOCX file with known metadata.

    The DOCX is built from plain XML parts to avoid committing binary fixtures.
    """

    path = base_dir / name
    relationships = RELATIONSHIPS_XML if include_custom else RELATIONSHIPS_XML_NO_CUSTOM
    document_relationships = (
        DOCUMENT_RELS_WITH_CUSTOM_XML if include_custom_xml else EMPTY_RELS_XML
    )

    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", _content_types_xml(include_custom))
        zf.writestr("_rels/.rels", relationships)
        zf.writestr("docProps/core.xml", CORE_XML)
        zf.writestr("docProps/app.xml", APP_XML)
        if include_custom:
            zf.writestr("docProps/custom.xml", CUSTOM_XML)
        zf.writestr("word/document.xml", DOCUMENT_XML)
        zf.writestr("word/_rels/document.xml.rels", document_relationships)
        if include_custom_xml:
            zf.writestr("customXml/item1.xml", CUSTOM_XML_ITEM_ONE)
            zf.writestr("customXml/item2.xml", CUSTOM_XML_ITEM_TWO)

    return path


def create_boilerplate_docx(
    base_dir: Path,
    name: str,
    *,
    header_text: str = "",
    footer_text: str = "",
    body_paragraphs: list[str] | None = None,
) -> Path:
    """Create a DOCX file with controllable header/footer/body content."""

    body_paragraphs = body_paragraphs or ["Hello"]
    path = base_dir / name

    document_body = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="{WORD_NAMESPACE}" xmlns:r="{RELATIONSHIP_NAMESPACE}">
          <w:body>
        {_wrap_paragraphs(body_paragraphs)}
            <w:sectPr>
              <w:headerReference w:type="default" r:id="rId1"/>
              <w:footerReference w:type="default" r:id="rId2"/>
            </w:sectPr>
          </w:body>
        </w:document>
        """
    ).strip()

    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", _content_types_with_header_footer(body_paragraphs))
        zf.writestr("_rels/.rels", RELATIONSHIPS_WITH_DOCUMENT)
        zf.writestr("word/document.xml", document_body)
        zf.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS_WITH_HEADER_FOOTER)
        zf.writestr("word/header1.xml", HEADER_XML.format(header_text=escape(header_text)))
        zf.writestr("word/footer1.xml", FOOTER_XML.format(footer_text=escape(footer_text)))

    return path


def create_outline_docx(base_dir: Path, name: str) -> Path:
    """Create a DOCX file with paragraphs exercising numbering detection."""

    path = base_dir / name

    document_body = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="{WORD_NAMESPACE}" xmlns:r="{RELATIONSHIP_NAMESPACE}">
          <w:body>
            <w:p>
              <w:pPr><w:pStyle w:val="BodyText"/></w:pPr>
              <w:r><w:t>1. Manual number</w:t></w:r>
            </w:p>
            <w:p>
              <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
              <w:r><w:t>(a) Heading example</w:t></w:r>
            </w:p>
            <w:p>
              <w:pPr>
                <w:pStyle w:val="BodyText"/>
                <w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>
              </w:pPr>
              <w:r><w:t>Auto numbered paragraph</w:t></w:r>
            </w:p>
            <w:p>
              <w:pPr>
                <w:pStyle w:val="ArticleTitle"/>
                <w:numPr><w:ilvl w:val="1"/><w:numId w:val="2"/></w:numPr>
              </w:pPr>
              <w:r><w:t>Section heading</w:t></w:r>
            </w:p>
          </w:body>
        </w:document>
        """
    ).strip()

    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES_WITH_STYLES)
        zf.writestr("_rels/.rels", RELATIONSHIPS_WITH_DOCUMENT)
        zf.writestr("word/document.xml", document_body)
        zf.writestr("word/styles.xml", STYLES_XML)
        zf.writestr("word/_rels/document.xml.rels", EMPTY_RELS_XML)

    return path


def create_notes_docx(
    base_dir: Path,
    name: str,
    *,
    footnote_text: str = "Footnote text",
    endnote_text: str = "Endnote text",
) -> Path:
    """Create a DOCX file containing a footnote and endnote reference."""

    path = base_dir / name

    document_body = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="{WORD_NAMESPACE}" xmlns:r="{RELATIONSHIP_NAMESPACE}">
          <w:body>
            <w:p>
              <w:r><w:t>Body with footnote</w:t></w:r>
              <w:r><w:footnoteReference w:id="1"/></w:r>
              <w:r><w:t> continues.</w:t></w:r>
            </w:p>
            <w:p>
              <w:r><w:t>Body with endnote</w:t></w:r>
              <w:r><w:endnoteReference w:id="2"/></w:r>
            </w:p>
          </w:body>
        </w:document>
        """
    ).strip()

    footnotes_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:footnotes xmlns:w="{WORD_NAMESPACE}">
          <w:footnote w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>
          <w:footnote w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>
          <w:footnote w:id="1"><w:p><w:r><w:t>{escape(footnote_text)}</w:t></w:r></w:p></w:footnote>
        </w:footnotes>
        """
    ).strip()

    endnotes_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:endnotes xmlns:w="{WORD_NAMESPACE}">
          <w:endnote w:id="0"><w:p><w:r><w:separator/></w:r></w:p></w:endnote>
          <w:endnote w:id="2"><w:p><w:r><w:t>{escape(endnote_text)}</w:t></w:r></w:p></w:endnote>
        </w:endnotes>
        """
    ).strip()

    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", _content_types_with_notes())
        zf.writestr("_rels/.rels", RELATIONSHIPS_WITH_DOCUMENT)
        zf.writestr("word/document.xml", document_body)
        zf.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS_WITH_NOTES)
        zf.writestr("word/footnotes.xml", footnotes_xml)
        zf.writestr("word/endnotes.xml", endnotes_xml)

    return path


def create_multistory_notes_docx(base_dir: Path, name: str) -> Path:
    """Create a DOCX file with note references in multiple stories."""

    path = base_dir / name

    document_body = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="{WORD_NAMESPACE}" xmlns:r="{RELATIONSHIP_NAMESPACE}">
          <w:body>
            <w:p>
              <w:r><w:t>Body footnote</w:t></w:r>
              <w:r><w:footnoteReference w:id="1"/></w:r>
            </w:p>
            <w:p>
              <w:r><w:t>Body endnote</w:t></w:r>
              <w:r><w:endnoteReference w:id="3"/></w:r>
            </w:p>
            <w:sectPr>
              <w:headerReference w:type="first" r:id="rId1"/>
              <w:footerReference w:type="first" r:id="rId2"/>
            </w:sectPr>
          </w:body>
        </w:document>
        """
    ).strip()

    header_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:hdr xmlns:w="{WORD_NAMESPACE}" xmlns:r="{RELATIONSHIP_NAMESPACE}">
          <w:p>
            <w:r><w:t>Header footnote</w:t></w:r>
            <w:r><w:footnoteReference w:id="2"/></w:r>
          </w:p>
        </w:hdr>
        """
    ).strip()

    footer_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:ftr xmlns:w="{WORD_NAMESPACE}" xmlns:r="{RELATIONSHIP_NAMESPACE}">
          <w:p>
            <w:r><w:t>Footer endnote</w:t></w:r>
            <w:r><w:endnoteReference w:id="3"/></w:r>
          </w:p>
        </w:ftr>
        """
    ).strip()

    footnotes_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:footnotes xmlns:w="{WORD_NAMESPACE}">
          <w:footnote w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>
          <w:footnote w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>
          <w:footnote w:id="1"><w:p><w:r><w:t>Main footnote text</w:t></w:r></w:p></w:footnote>
          <w:footnote w:id="2"><w:p><w:r><w:t>Header footnote text</w:t></w:r><w:r><w:endnoteReference w:id="3"/></w:r></w:p></w:footnote>
        </w:footnotes>
        """
    ).strip()

    endnotes_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:endnotes xmlns:w="{WORD_NAMESPACE}">
          <w:endnote w:id="0"><w:p><w:r><w:separator/></w:r></w:p></w:endnote>
          <w:endnote w:id="3"><w:p><w:r><w:t>Shared endnote text</w:t></w:r></w:p></w:endnote>
        </w:endnotes>
        """
    ).strip()

    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", _content_types_for_changes())
        zf.writestr("_rels/.rels", RELATIONSHIPS_WITH_DOCUMENT)
        zf.writestr("word/document.xml", document_body)
        zf.writestr("word/header1.xml", header_xml)
        zf.writestr("word/footer1.xml", footer_xml)
        zf.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS_WITH_CHANGES)
        zf.writestr("word/footnotes.xml", footnotes_xml)
        zf.writestr("word/endnotes.xml", endnotes_xml)

    return path


def create_comments_docx(base_dir: Path, name: str) -> Path:
    """Create a DOCX file containing threaded/resolved comments."""

    path = base_dir / name

    document_body = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="{WORD_NAMESPACE}">
          <w:body>
            <w:p>
              <w:r><w:t>Body with </w:t></w:r>
              <w:commentRangeStart w:id="1" />
              <w:r><w:t>parent range</w:t></w:r>
              <w:commentRangeEnd w:id="1" />
              <w:r><w:commentReference w:id="1"/></w:r>
            </w:p>
            <w:p>
              <w:r><w:t>More text before </w:t></w:r>
              <w:commentRangeStart w:id="2" />
              <w:r><w:t>child range</w:t></w:r>
              <w:commentRangeEnd w:id="2" />
              <w:r><w:t> after comment</w:t></w:r>
              <w:r><w:commentReference w:id="2"/></w:r>
            </w:p>
          </w:body>
        </w:document>
        """
    ).strip()

    comments_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:comments xmlns:w="{WORD_NAMESPACE}" xmlns:w14="{W14_NAMESPACE}">
          <w:comment w:id="1" w:author="Alice" w:initials="AL" w:date="2024-01-02T10:00:00Z">
            <w:p w14:paraId="11111111" w14:textId="AAAA1111"><w:r><w:t>Parent comment</w:t></w:r></w:p>
            <w:p w14:paraId="33333333" w14:textId="CCCC3333"><w:r><w:t>Second paragraph</w:t></w:r></w:p>
          </w:comment>
          <w:comment w:id="2" w:author="Bob">
            <w:p w14:paraId="22222222" w14:textId="BBBB2222"><w:r><w:t>Child comment</w:t></w:r></w:p>
          </w:comment>
        </w:comments>
        """
    ).strip()

    comments_extended_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w15:commentsEx xmlns:w15="{W15_NAMESPACE}">
          <w15:commentEx w15:paraId="11111111" w15:done="1" />
          <w15:commentEx w15:paraId="22222222" w15:paraIdParent="11111111" />
        </w15:commentsEx>
        """
    ).strip()

    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", _content_types_with_comments())
        zf.writestr("_rels/.rels", RELATIONSHIPS_WITH_DOCUMENT)
        zf.writestr("word/document.xml", document_body)
        zf.writestr("word/_rels/document.xml.rels", EMPTY_RELS_XML)
        zf.writestr("word/comments.xml", comments_xml)
        zf.writestr("word/commentsExtended.xml", comments_extended_xml)

    return path


def create_changes_docx(base_dir: Path, name: str) -> Path:
    """Create a DOCX file containing tracked changes across stories."""

    path = base_dir / name

    document_body = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="{WORD_NAMESPACE}" xmlns:r="{RELATIONSHIP_NAMESPACE}">
          <w:body>
            <w:p>
              <w:r><w:t>Base </w:t></w:r>
              <w:ins w:author="Alice" w:date="2024-01-02T10:00:00Z"><w:r><w:t>inserted</w:t></w:r></w:ins>
              <w:r><w:t> text</w:t></w:r>
            </w:p>
            <w:p>
              <w:r><w:t>Footnote story</w:t></w:r>
              <w:r><w:footnoteReference w:id="1"/></w:r>
            </w:p>
            <w:p>
              <w:r><w:t>Endnote story</w:t></w:r>
              <w:r><w:endnoteReference w:id="2"/></w:r>
            </w:p>
            <w:sectPr>
              <w:headerReference w:type="default" r:id="rId1"/>
              <w:footerReference w:type="default" r:id="rId2"/>
            </w:sectPr>
          </w:body>
        </w:document>
        """
    ).strip()

    header_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:hdr xmlns:w="{WORD_NAMESPACE}" xmlns:r="{RELATIONSHIP_NAMESPACE}">
          <w:p><w:del w:author="Bob" w:date="2024-01-03T12:00:00Z"><w:r><w:delText>Header change</w:delText></w:r></w:del></w:p>
        </w:hdr>
        """
    ).strip()

    footer_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:ftr xmlns:w="{WORD_NAMESPACE}" xmlns:r="{RELATIONSHIP_NAMESPACE}">
          <w:p><w:moveFrom w:author="Cara" w:date="2024-01-04T09:00:00Z"><w:r><w:t>Moved away</w:t></w:r></w:moveFrom></w:p>
        </w:ftr>
        """
    ).strip()

    footnotes_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:footnotes xmlns:w="{WORD_NAMESPACE}">
          <w:footnote w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>
          <w:footnote w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>
          <w:footnote w:id="1"><w:p><w:moveTo w:author="Dan" w:date="2024-01-05T08:00:00Z"><w:r><w:t>Moved here</w:t></w:r></w:moveTo></w:p></w:footnote>
        </w:footnotes>
        """
    ).strip()

    endnotes_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:endnotes xmlns:w="{WORD_NAMESPACE}">
          <w:endnote w:id="0"><w:p><w:r><w:separator/></w:r></w:p></w:endnote>
          <w:endnote w:id="2"><w:p><w:ins w:author="Eve" w:date="2024-01-06T14:00:00Z"><w:r><w:t>Endnote insert</w:t></w:r></w:ins></w:p></w:endnote>
        </w:endnotes>
        """
    ).strip()

    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", _content_types_for_changes())
        zf.writestr("_rels/.rels", RELATIONSHIPS_WITH_DOCUMENT)
        zf.writestr("word/document.xml", document_body)
        zf.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS_WITH_CHANGES)
        zf.writestr("word/header1.xml", header_xml)
        zf.writestr("word/footer1.xml", footer_xml)
        zf.writestr("word/footnotes.xml", footnotes_xml)
        zf.writestr("word/endnotes.xml", endnotes_xml)

    return path


def create_highlights_docx(base_dir: Path, name: str) -> Path:
    """Create a DOCX file containing highlighted text across stories."""

    path = base_dir / name

    document_body = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="{WORD_NAMESPACE}" xmlns:r="{RELATIONSHIP_NAMESPACE}">
          <w:body>
            <w:p>
              <w:r><w:t>Normal </w:t></w:r>
              <w:r><w:rPr><w:highlight w:val="yellow"/></w:rPr><w:t>body highlight</w:t></w:r>
              <w:r><w:t> after.</w:t></w:r>
            </w:p>
            <w:p>
              <w:r><w:t>Footnote ref</w:t></w:r>
              <w:r><w:footnoteReference w:id="1"/></w:r>
            </w:p>
            <w:p>
              <w:r><w:t>Endnote ref</w:t></w:r>
              <w:r><w:endnoteReference w:id="2"/></w:r>
            </w:p>
            <w:sectPr>
              <w:headerReference w:type="default" r:id="rId1"/>
              <w:footerReference w:type="default" r:id="rId2"/>
            </w:sectPr>
          </w:body>
        </w:document>
        """
    ).strip()

    header_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:hdr xmlns:w="{WORD_NAMESPACE}" xmlns:r="{RELATIONSHIP_NAMESPACE}">
          <w:p><w:r><w:rPr><w:highlight w:val="green"/></w:rPr><w:t>Header highlight</w:t></w:r></w:p>
        </w:hdr>
        """
    ).strip()

    footer_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:ftr xmlns:w="{WORD_NAMESPACE}" xmlns:r="{RELATIONSHIP_NAMESPACE}">
          <w:p><w:r><w:rPr><w:highlight w:val="cyan"/></w:rPr><w:t>Footer highlight</w:t></w:r></w:p>
        </w:ftr>
        """
    ).strip()

    footnotes_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:footnotes xmlns:w="{WORD_NAMESPACE}">
          <w:footnote w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>
          <w:footnote w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>
          <w:footnote w:id="1"><w:p><w:r><w:rPr><w:highlight w:val="pink"/></w:rPr><w:t>Footnote highlight</w:t></w:r></w:p></w:footnote>
        </w:footnotes>
        """
    ).strip()

    endnotes_xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:endnotes xmlns:w="{WORD_NAMESPACE}">
          <w:endnote w:id="0"><w:p><w:r><w:separator/></w:r></w:p></w:endnote>
          <w:endnote w:id="2"><w:p><w:r><w:rPr><w:highlight w:val="blue"/></w:rPr><w:t>Endnote highlight</w:t></w:r></w:p></w:endnote>
        </w:endnotes>
        """
    ).strip()

    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", _content_types_for_changes())
        zf.writestr("_rels/.rels", RELATIONSHIPS_WITH_DOCUMENT)
        zf.writestr("word/document.xml", document_body)
        zf.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS_WITH_CHANGES)
        zf.writestr("word/header1.xml", header_xml)
        zf.writestr("word/footer1.xml", footer_xml)
        zf.writestr("word/footnotes.xml", footnotes_xml)
        zf.writestr("word/endnotes.xml", endnotes_xml)

    return path
