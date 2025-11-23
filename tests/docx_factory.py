"""Helpers for building DOCX fixtures on the fly without storing binaries."""
from __future__ import annotations

from pathlib import Path
import textwrap
import zipfile


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
