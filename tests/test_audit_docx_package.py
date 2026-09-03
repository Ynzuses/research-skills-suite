from __future__ import annotations

import contextlib
import hashlib
import importlib.util
from io import StringIO
from pathlib import Path
import unittest
import uuid
import warnings
import zipfile


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "research-document-delivery"
    / "scripts"
    / "audit_docx_package.py"
)
SPEC = importlib.util.spec_from_file_location("audit_docx_package", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  {main_document_override}
  {extra}
</Types>
"""

MAIN_DOCUMENT_OVERRIDE = (
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
)

DOCUMENT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>{body}<w:sectPr/></w:body>
</w:document>
"""

COMMENTS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:comment w:id="0" w:author="Researcher"><w:p><w:r><w:t>Review</w:t></w:r></w:p></w:comment>
</w:comments>
"""

RELATIONSHIPS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {relationships}
</Relationships>
"""

OFFICE_DOCUMENT_RELATIONSHIP = (
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/>'
)
ROOT_RELATIONSHIPS = RELATIONSHIPS.format(
    relationships=OFFICE_DOCUMENT_RELATIONSHIP
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_docx(
    path: Path,
    *,
    body: str = "<w:p><w:r><w:t>Hello</w:t></w:r></w:p>",
    main_document_override: str = MAIN_DOCUMENT_OVERRIDE,
    content_type_extra: str = "",
    content_types_xml: str | None = None,
    document_xml: str | None = None,
    root_relationships_xml: str | None = ROOT_RELATIONSHIPS,
    relationships: str | None = None,
    extra_parts: dict[str, str] | None = None,
) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            content_types_xml
            if content_types_xml is not None
            else CONTENT_TYPES.format(
                main_document_override=main_document_override,
                extra=content_type_extra,
            ),
        )
        if root_relationships_xml is not None:
            archive.writestr("_rels/.rels", root_relationships_xml)
        archive.writestr(
            "word/document.xml",
            document_xml if document_xml is not None else DOCUMENT.format(body=body),
        )
        if relationships is not None:
            archive.writestr(
                "word/_rels/document.xml.rels",
                RELATIONSHIPS.format(relationships=relationships),
            )
        for name, value in sorted((extra_parts or {}).items()):
            archive.writestr(name, value)


class AuditDocxPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parent
        self.prefix = f"_audit_docx_{uuid.uuid4().hex}"

    def tearDown(self) -> None:
        for generated in self.root.glob(f"{self.prefix}-*"):
            if generated.is_file() or generated.is_symlink():
                generated.unlink()

    def fixture_path(self, name: str) -> Path:
        return self.root / f"{self.prefix}-{name}"

    def test_minimal_package_is_ok_and_is_not_modified(self) -> None:
        path = self.fixture_path("minimal.docx")
        _write_docx(path)
        before = _sha256(path)

        result = AUDIT.audit_docx(path)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["summary"]["issues"], 0)
        self.assertTrue(result["package"]["deep_audit_complete"])
        self.assertEqual(before, _sha256(path))

    def test_missing_root_relationships_is_an_error(self) -> None:
        path = self.fixture_path("missing-root-rels.docx")
        _write_docx(path, root_relationships_xml=None)

        result = AUDIT.audit_docx(path)

        self.assertEqual(result["status"], "read_error")
        self.assertIn(
            "missing_package_relationships_part",
            {finding["code"] for finding in result["findings"]},
        )

    def test_root_relationships_without_office_document_is_an_error(self) -> None:
        path = self.fixture_path("missing-office-document-rel.docx")
        root_relationships = RELATIONSHIPS.format(
            relationships=(
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
                'Target="docProps/core.xml"/>'
            )
        )
        core_override = (
            '<Override PartName="/docProps/core.xml" '
            'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        )
        _write_docx(
            path,
            root_relationships_xml=root_relationships,
            content_type_extra=core_override,
            extra_parts={"docProps/core.xml": "<coreProperties/>"},
        )

        result = AUDIT.audit_docx(path)

        self.assertEqual(result["status"], "read_error")
        self.assertIn(
            "missing_office_document_relationship",
            {finding["code"] for finding in result["findings"]},
        )

    def test_fake_package_namespaces_are_errors(self) -> None:
        fake_content_types = CONTENT_TYPES.format(
            main_document_override=MAIN_DOCUMENT_OVERRIDE,
            extra="",
        ).replace(
            "http://schemas.openxmlformats.org/package/2006/content-types",
            "urn:fake:content-types",
        )
        fake_relationships = ROOT_RELATIONSHIPS.replace(
            "http://schemas.openxmlformats.org/package/2006/relationships",
            "urn:fake:relationships",
        )
        fake_document = DOCUMENT.format(body="<w:p/>").replace(
            "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
            "urn:fake:wordprocessingml",
        )
        cases = (
            (
                "content-types",
                {"content_types_xml": fake_content_types},
                "invalid_content_types_root",
            ),
            (
                "relationships",
                {"root_relationships_xml": fake_relationships},
                "invalid_relationships_root",
            ),
            (
                "document",
                {"document_xml": fake_document},
                "invalid_main_document_root",
            ),
        )

        for name, kwargs, expected_code in cases:
            with self.subTest(name=name):
                path = self.fixture_path(f"fake-{name}.docx")
                _write_docx(path, **kwargs)

                result = AUDIT.audit_docx(path)
                errors = {
                    finding["code"]
                    for finding in result["findings"]
                    if finding["severity"] == "error"
                }

                self.assertEqual(result["status"], "read_error")
                self.assertIn(expected_code, errors)

    def test_missing_main_document_content_type_is_an_error(self) -> None:
        path = self.fixture_path("missing-main-content-type.docx")
        _write_docx(path, main_document_override="")

        result = AUDIT.audit_docx(path)

        self.assertEqual(result["status"], "read_error")
        self.assertIn(
            "missing_main_document_content_type",
            {finding["code"] for finding in result["findings"]},
        )

    def test_uncovered_package_part_is_an_error(self) -> None:
        path = self.fixture_path("uncovered-part.docx")
        _write_docx(path, extra_parts={"word/media/image1.png": "not-an-image"})

        result = AUDIT.audit_docx(path)
        findings = {
            finding["code"]: finding for finding in result["findings"]
        }

        self.assertEqual(result["status"], "read_error")
        self.assertIn("package_parts_missing_content_type", findings)
        self.assertIn(
            "word/media/image1.png",
            findings["package_parts_missing_content_type"]["details"],
        )

    def test_encoded_or_traversing_content_type_part_name_is_an_error(self) -> None:
        unsafe_part_names = (
            "/word%2Fdocument.xml",
            "/../word/document.xml",
        )
        for index, part_name in enumerate(unsafe_part_names):
            with self.subTest(part_name=part_name):
                path = self.fixture_path(f"unsafe-content-type-{index}.docx")
                unsafe_override = (
                    f'<Override PartName="{part_name}" '
                    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                )
                _write_docx(path, main_document_override=unsafe_override)

                result = AUDIT.audit_docx(path)
                unsafe_findings = [
                    finding
                    for finding in result["findings"]
                    if finding["code"] == "unsafe_content_type_part_name"
                ]

                self.assertEqual(result["status"], "read_error")
                self.assertEqual(len(unsafe_findings), 1)
                self.assertEqual(unsafe_findings[0]["severity"], "error")

    def test_invalid_main_document_root_or_body_is_an_error(self) -> None:
        invalid_root = DOCUMENT.format(body="<w:p/>").replace(
            "<w:document ", "<w:notDocument ", 1
        ).replace("</w:document>", "</w:notDocument>")
        missing_body = DOCUMENT.format(body="<w:p/>").replace(
            "<w:body><w:p/><w:sectPr/></w:body>", "<w:p/>"
        )
        cases = (
            ("root", invalid_root, "invalid_main_document_root"),
            ("body", missing_body, "invalid_main_document_body"),
        )

        for name, document_xml, expected_code in cases:
            with self.subTest(name=name):
                path = self.fixture_path(f"invalid-document-{name}.docx")
                _write_docx(path, document_xml=document_xml)

                result = AUDIT.audit_docx(path)

                self.assertEqual(result["status"], "read_error")
                self.assertIn(
                    expected_code,
                    {finding["code"] for finding in result["findings"]},
                )

    def test_consistent_visible_comment_markup_is_informational(self) -> None:
        path = self.fixture_path("reviewed.docx")
        body = """
        <w:p>
          <w:commentRangeStart w:id="0"/>
          <w:r><w:t>Reviewed text</w:t></w:r>
          <w:commentRangeEnd w:id="0"/>
          <w:r><w:commentReference w:id="0"/></w:r>
        </w:p>
        """
        comment_override = (
            '<Override PartName="/word/comments.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>'
        )
        relationship = (
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" '
            'Target="comments.xml"/>'
        )
        _write_docx(
            path,
            body=body,
            content_type_extra=comment_override,
            relationships=relationship,
            extra_parts={"word/comments.xml": COMMENTS},
        )

        result = AUDIT.audit_docx(path)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["metrics"]["comment_markers"]["commentReference"], 1)
        self.assertEqual(result["metrics"]["comment_definitions"], 1)
        self.assertIn(
            "visible_comment_markup_present",
            {finding["code"] for finding in result["findings"]},
        )

    def test_comment_relationship_and_content_type_without_markers_are_residue(self) -> None:
        path = self.fixture_path("residue.docx")
        comment_override = (
            '<Override PartName="/word/comments.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>'
        )
        relationship = (
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" '
            'Target="comments.xml"/>'
        )
        _write_docx(
            path,
            content_type_extra=comment_override,
            relationships=relationship,
            extra_parts={"word/comments.xml": COMMENTS},
        )

        result = AUDIT.audit_docx(path)
        codes = {finding["code"] for finding in result["findings"]}

        self.assertEqual(result["status"], "issues")
        self.assertIn("residual_comment_family_parts", codes)
        self.assertIn("residual_comment_relationships", codes)
        self.assertIn("residual_comment_content_types", codes)

    def test_features_are_reported_without_causing_failure(self) -> None:
        path = self.fixture_path("features.docx")
        body = """
        <w:p>
          <w:ins w:id="1"><w:r><w:t>Inserted</w:t></w:r></w:ins>
          <w:fldSimple w:instr="PAGE"><w:r><w:t>1</w:t></w:r></w:fldSimple>
          <m:oMath><m:r><m:t>x</m:t></m:r></m:oMath>
        </w:p>
        """
        _write_docx(path, body=body)

        result = AUDIT.audit_docx(path)
        codes = {finding["code"] for finding in result["findings"]}

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["metrics"]["tracked_changes"]["ins"], 1)
        self.assertEqual(result["metrics"]["field_codes"]["fldSimple"], 1)
        self.assertEqual(result["metrics"]["equations"]["oMath"], 1)
        self.assertTrue(
            {"tracked_changes_present", "field_codes_present", "equations_present"}
            <= codes
        )

    def test_missing_internal_relationship_target_is_an_issue(self) -> None:
        path = self.fixture_path("dangling.docx")
        relationship = (
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" '
            'Target="settings.xml"/>'
        )
        _write_docx(path, relationships=relationship)

        result = AUDIT.audit_docx(path)

        self.assertEqual(result["status"], "issues")
        self.assertIn(
            "missing_relationship_target",
            {finding["code"] for finding in result["findings"]},
        )
        self.assertEqual(len(result["metrics"]["missing_relationship_targets"]), 1)

    def test_local_file_external_relationship_is_an_error(self) -> None:
        path = self.fixture_path("local-file-link.docx")
        relationship = (
            '<Relationship Id="rIdExternal" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
            'Target="file:///C:/private/source.txt" TargetMode="External"/>'
        )
        _write_docx(path, relationships=relationship)

        result = AUDIT.audit_docx(path)

        self.assertEqual(result["status"], "read_error")
        self.assertIn(
            "local_file_external_relationship",
            {finding["code"] for finding in result["findings"]},
        )

    def test_https_external_hyperlink_remains_valid(self) -> None:
        path = self.fixture_path("https-link.docx")
        body = (
            '<w:p><w:hyperlink r:id="rIdExternal">'
            '<w:r><w:t>Source</w:t></w:r></w:hyperlink></w:p>'
        )
        relationship = (
            '<Relationship Id="rIdExternal" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
            'Target="https://example.org/source" TargetMode="External"/>'
        )
        _write_docx(path, body=body, relationships=relationship)

        result = AUDIT.audit_docx(path)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["summary"]["errors"], 0)
        self.assertEqual(
            result["metrics"]["external_relationships"][0]["target"],
            "https://example.org/source",
        )

    def test_encoded_separator_and_relationship_escape_are_errors(self) -> None:
        targets = (
            "%2e%2e%2f%2e%2e%2foutside.xml",
            "../../../outside.xml",
        )
        for index, target in enumerate(targets):
            with self.subTest(target=target):
                path = self.fixture_path(f"unsafe-target-{index}.docx")
                relationship = (
                    '<Relationship Id="rIdUnsafe" '
                    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" '
                    f'Target="{target}"/>'
                )
                _write_docx(path, relationships=relationship)

                result = AUDIT.audit_docx(path)
                error_codes = {
                    finding["code"]
                    for finding in result["findings"]
                    if finding["severity"] == "error"
                }

                self.assertEqual(result["status"], "read_error")
                self.assertIn("unsafe_relationship_target", error_codes)

    def test_percent_encoded_zip_separator_is_rejected_as_an_error(self) -> None:
        path = self.fixture_path("encoded-zip-path.docx")
        _write_docx(
            path,
            extra_parts={"word%2F..%2Foutside.xml": "unsafe"},
        )

        report = AUDIT.audit_paths([path])

        self.assertEqual(report["exit_code"], 2)
        self.assertEqual(report["files"][0]["status"], "read_error")
        unsafe = next(
            finding
            for finding in report["files"][0]["findings"]
            if finding["code"] == "unsafe_zip_path"
        )
        self.assertEqual(unsafe["severity"], "error")

    def test_duplicate_zip_entry_is_rejected_with_issue_exit(self) -> None:
        path = self.fixture_path("duplicate.docx")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    "[Content_Types].xml",
                    CONTENT_TYPES.format(
                        main_document_override=MAIN_DOCUMENT_OVERRIDE,
                        extra="",
                    ),
                )
                archive.writestr("word/document.xml", DOCUMENT.format(body=""))
                archive.writestr("word/document.xml", DOCUMENT.format(body=""))

        report = AUDIT.audit_paths([path])

        self.assertEqual(report["exit_code"], 1)
        self.assertEqual(report["files"][0]["status"], "issues")
        self.assertTrue(report["files"][0]["package"]["rejected_for_safe_audit"])

    def test_path_escape_is_rejected_without_extraction(self) -> None:
        path = self.fixture_path("escape.docx")
        outside = self.root.parent / f"{self.prefix}-escaped.xml"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(f"../{outside.name}", "unsafe")

        report = AUDIT.audit_paths([path])

        self.assertEqual(report["exit_code"], 2)
        self.assertEqual(report["files"][0]["status"], "read_error")
        self.assertFalse(outside.exists())
        self.assertIn(
            "unsafe_zip_path",
            {finding["code"] for finding in report["files"][0]["findings"]},
        )

    def test_invalid_zip_is_a_read_error(self) -> None:
        path = self.fixture_path("broken.docx")
        path.write_bytes(b"not a zip package")

        report = AUDIT.audit_paths([path])

        self.assertEqual(report["exit_code"], 2)
        self.assertEqual(report["files"][0]["status"], "read_error")

    def test_json_cli_exit_code_and_output(self) -> None:
        path = self.fixture_path("minimal.docx")
        _write_docx(path)
        output = StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = AUDIT.main(["--format", "json", str(path)])

        self.assertEqual(exit_code, 0)
        self.assertIn('"schema_version": 1', output.getvalue())
        self.assertIn('"exit_code": 0', output.getvalue())


if __name__ == "__main__":
    unittest.main()
