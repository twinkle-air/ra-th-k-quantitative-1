from __future__ import annotations

import copy
import io
import re
import zipfile
from datetime import datetime
from html import escape
from typing import Any
from xml.etree import ElementTree as ET

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen.canvas import Canvas


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
ET.register_namespace("w", WORD_NS)

TOKEN_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")
RTF_TOKEN_PATTERN = re.compile(
    r"(?:\\\{|\{)(?:\\\{|\{)\s*([a-zA-Z0-9_.-]+)\s*(?:\\\}|\})(?:\\\}|\})"
)
SAMPLE_PREFIX = "sample."

SCALAR_TOKENS = {
    "report.title",
    "report.generated_at",
    "report.language",
    "report.sample_count",
    "standard.name",
    "standard.live_time_s",
    "standard.calibration_equation",
    "standard.correlation_r",
    "standard.deviation_percent",
    "standard.rms_keV",
    "method.note",
}

SAMPLE_TOKENS = {
    "sample.no",
    "sample.name",
    "sample.mass_g",
    "sample.ra_ppm",
    "sample.th_ppm",
    "sample.k_percent",
    "sample.ra_bq_kg",
    "sample.th_bq_kg",
    "sample.k_bq_kg",
    "sample.qc",
    "sample.calibration_equation",
    "sample.correlation_r",
    "sample.deviation_percent",
    "sample.rms_keV",
    "sample.warnings",
}

SUPPORTED_TOKENS = SCALAR_TOKENS | SAMPLE_TOKENS
INDEXED_SAMPLE_PATTERN = re.compile(r"sample\.(\d+)\.(.+)")

LANGUAGE_LABELS = {
    "zh": {
        "title": "土壤镭钍钾定量分析报告",
        "language": "简体中文",
        "pass": "通过",
        "review": "需复核",
        "method": "HPGe γ 能谱相对效率同几何比较法；结果应结合实验室质量控制复核。",
    },
    "zht": {
        "title": "土壤鐳釷鉀定量分析報告",
        "language": "繁體中文",
        "pass": "通過",
        "review": "需複核",
        "method": "HPGe γ 能譜相對效率同幾何比較法；結果應結合實驗室品質控制複核。",
    },
    "en": {
        "title": "Soil Ra-Th-K Quantitative Analysis Report",
        "language": "English",
        "pass": "Pass",
        "review": "Review required",
        "method": "HPGe gamma spectrometry by matched-geometry relative efficiency; results require laboratory QC review.",
    },
    "fr": {
        "title": "Rapport d’analyse quantitative Ra-Th-K du sol",
        "language": "Français",
        "pass": "Conforme",
        "review": "À vérifier",
        "method": "Spectrométrie gamma HPGe par efficacité relative à géométrie identique ; les résultats exigent une revue CQ du laboratoire.",
    },
}


def _number(value: Any, digits: int = 8) -> str:
    if not isinstance(value, (int, float)):
        return "—"
    return f"{float(value):.{digits}g}"


def _calibration_equation(calibration: dict[str, Any] | None) -> str:
    calibration = calibration or {}
    slope = calibration.get("slope")
    intercept = calibration.get("intercept")
    if not isinstance(slope, (int, float)) or not isinstance(intercept, (int, float)):
        return "—"
    sign = "−" if intercept < 0 else "+"
    return f"E = {_number(slope)} × CH {sign} {_number(abs(intercept))} keV"


def _document_xml_names(archive: zipfile.ZipFile) -> list[str]:
    names = set(archive.namelist())
    if "word/document.xml" not in names:
        raise ValueError("报告模板不是有效的 DOCX 文件：缺少 word/document.xml。")
    return sorted(
        name for name in names
        if name == "word/document.xml"
        or re.fullmatch(r"word/(header|footer)\d+\.xml", name)
    )


def _read_docx_parts(template: bytes) -> tuple[zipfile.ZipFile, io.BytesIO, list[str]]:
    source = io.BytesIO(template)
    if not zipfile.is_zipfile(source):
        raise ValueError("报告模板必须是有效的 .docx 文件。")
    source.seek(0)
    archive = zipfile.ZipFile(source, "r")
    return archive, source, _document_xml_names(archive)


def _tokens_in_xml(xml_bytes: bytes) -> set[str]:
    root = ET.fromstring(xml_bytes)
    text = "".join(node.text or "" for node in root.iter(f"{{{WORD_NS}}}t"))
    return set(TOKEN_PATTERN.findall(text))


def _inspect_docx_template(filename: str, template: bytes) -> dict[str, Any]:
    archive, source, xml_names = _read_docx_parts(template)
    try:
        tokens: set[str] = set()
        for name in xml_names:
            tokens.update(_tokens_in_xml(archive.read(name)))
    finally:
        archive.close()
        source.close()
    recognized = sorted(tokens & SUPPORTED_TOKENS)
    unknown = sorted(tokens - SUPPORTED_TOKENS)
    if not recognized:
        raise ValueError("模板中未找到可识别占位符。请先下载示例模板或按说明添加 {{report.*}} / {{sample.*}} 占位符。")
    return {
        "filename": filename,
        "format": "docx",
        "recognized_tokens": recognized,
        "unknown_tokens": unknown,
        "recognized_count": len(recognized),
        "has_sample_row": any(token.startswith(SAMPLE_PREFIX) for token in recognized),
    }


def _normalized_pdf_field(field_name: str) -> str:
    match = TOKEN_PATTERN.fullmatch(field_name.strip())
    return match.group(1) if match else field_name.strip()


def _is_supported_pdf_field(field_name: str) -> bool:
    if field_name in SUPPORTED_TOKENS:
        return True
    indexed = INDEXED_SAMPLE_PATTERN.fullmatch(field_name)
    return bool(indexed and f"sample.{indexed.group(2)}" in SAMPLE_TOKENS)


def _inspect_pdf_template(filename: str, template: bytes) -> dict[str, Any]:
    try:
        reader = PdfReader(io.BytesIO(template))
        fields = reader.get_fields() or {}
    except Exception as exc:
        raise ValueError(f"报告模板不是有效的 PDF 文件：{exc}") from exc
    if not fields:
        raise ValueError("PDF 报告模板必须包含可填写表单字段（AcroForm）；扫描版或纯版式 PDF 无法确定数据填入位置。")
    normalized = {_normalized_pdf_field(str(name)) for name in fields}
    recognized = sorted(name for name in normalized if _is_supported_pdf_field(name))
    unknown = sorted(normalized - set(recognized))
    if not recognized:
        raise ValueError("PDF 表单中未找到可识别字段。字段名应使用 report.title、standard.name 或 sample.1.name 等名称。")
    return {
        "filename": filename,
        "format": "pdf",
        "recognized_tokens": recognized,
        "unknown_tokens": unknown,
        "recognized_count": len(recognized),
        "has_sample_row": any(name.startswith(SAMPLE_PREFIX) for name in recognized),
    }


def _decode_rtf_doc(template: bytes) -> str:
    if not template.lstrip().startswith(b"{\\rtf"):
        raise ValueError("该 .doc 是旧式二进制 Word 文件。为避免依赖 Office/WPS 和宏风险，请先另存为 DOCX，或保存为 RTF 格式的 .doc。")
    return template.decode("latin-1")


def _inspect_doc_template(filename: str, template: bytes) -> dict[str, Any]:
    content = _decode_rtf_doc(template)
    tokens = set(RTF_TOKEN_PATTERN.findall(content))
    recognized = sorted(tokens & SUPPORTED_TOKENS)
    unknown = sorted(tokens - SUPPORTED_TOKENS)
    if not recognized:
        raise ValueError("DOC 模板中未找到可识别占位符。请添加 {{report.*}} / {{sample.*}} 占位符。")
    return {
        "filename": filename,
        "format": "doc",
        "recognized_tokens": recognized,
        "unknown_tokens": unknown,
        "recognized_count": len(recognized),
        "has_sample_row": any(token.startswith(SAMPLE_PREFIX) for token in recognized),
    }


def inspect_report_template(filename: str, template: bytes) -> dict[str, Any]:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "docx":
        return _inspect_docx_template(filename, template)
    if suffix == "doc":
        return _inspect_doc_template(filename, template)
    if suffix == "pdf":
        return _inspect_pdf_template(filename, template)
    raise ValueError("报告模板仅支持 .doc、.docx 或带表单字段的 .pdf 格式。")


def _replace_tokens_in_paragraph(paragraph: ET.Element, values: dict[str, str]) -> None:
    text_nodes = list(paragraph.iter(f"{{{WORD_NS}}}t"))
    if not text_nodes:
        return
    combined = "".join(node.text or "" for node in text_nodes)
    replaced = TOKEN_PATTERN.sub(lambda match: values.get(match.group(1), match.group(0)), combined)
    if replaced == combined:
        return
    text_nodes[0].text = replaced
    for node in text_nodes[1:]:
        node.text = ""


def _replace_tokens(root: ET.Element, values: dict[str, str]) -> None:
    for paragraph in root.iter(f"{{{WORD_NS}}}p"):
        _replace_tokens_in_paragraph(paragraph, values)


def _sample_values(row: dict[str, Any], labels: dict[str, str]) -> dict[str, str]:
    activity = row.get("activity_bq_kg") or {}
    calibration = row.get("calibration") or {}
    warnings = row.get("warnings") or []
    return {
        "sample.no": str(row.get("spectrum_no", "—")),
        "sample.name": str(row.get("name", "—")),
        "sample.mass_g": _number(row.get("mass_g")),
        "sample.ra_ppm": _number(row.get("ra_ppm")),
        "sample.th_ppm": _number(row.get("th_ppm")),
        "sample.k_percent": _number(row.get("k_percent")),
        "sample.ra_bq_kg": _number(activity.get("Ra226")),
        "sample.th_bq_kg": _number(activity.get("Th232")),
        "sample.k_bq_kg": _number(activity.get("K40")),
        "sample.qc": labels["review"] if warnings else labels["pass"],
        "sample.calibration_equation": _calibration_equation(calibration),
        "sample.correlation_r": _number(calibration.get("correlation_r")),
        "sample.deviation_percent": _number(calibration.get("relative_deviation_percent")),
        "sample.rms_keV": _number(calibration.get("rms_keV")),
        "sample.warnings": "；".join(str(item) for item in warnings) if warnings else labels["pass"],
    }


def _expand_sample_rows(root: ET.Element, results: list[dict[str, Any]], labels: dict[str, str]) -> None:
    for table in root.iter(f"{{{WORD_NS}}}tbl"):
        rows = list(table.findall(f"{{{WORD_NS}}}tr"))
        for row in rows:
            tokens = _tokens_in_xml(ET.tostring(row, encoding="utf-8"))
            if not any(token.startswith(SAMPLE_PREFIX) for token in tokens):
                continue
            position = list(table).index(row)
            table.remove(row)
            for offset, result in enumerate(results):
                clone = copy.deepcopy(row)
                _replace_tokens(clone, _sample_values(result, labels))
                table.insert(position + offset, clone)


def _scalar_values(analysis: dict[str, Any], language: str) -> dict[str, str]:
    labels = LANGUAGE_LABELS[language]
    standard = analysis.get("standard") or {}
    calibration = standard.get("calibration") or {}
    return {
        "report.title": labels["title"],
        "report.generated_at": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "report.language": labels["language"],
        "report.sample_count": str(len(analysis.get("results") or [])),
        "standard.name": str(standard.get("name", "—")),
        "standard.live_time_s": _number(standard.get("live_time_s")),
        "standard.calibration_equation": _calibration_equation(calibration),
        "standard.correlation_r": _number(calibration.get("correlation_r")),
        "standard.deviation_percent": _number(calibration.get("relative_deviation_percent")),
        "standard.rms_keV": _number(calibration.get("rms_keV")),
        "method.note": labels["method"],
    }


def _render_docx_template(template: bytes, analysis: dict[str, Any], language: str) -> bytes:
    if language not in LANGUAGE_LABELS:
        raise ValueError(f"Unsupported export language: {language}")
    _inspect_docx_template("template.docx", template)
    archive, source, xml_names = _read_docx_parts(template)
    output = io.BytesIO()
    labels = LANGUAGE_LABELS[language]
    try:
        replacements: dict[str, bytes] = {}
        for name in xml_names:
            root = ET.fromstring(archive.read(name))
            if name == "word/document.xml":
                _expand_sample_rows(root, list(analysis.get("results") or []), labels)
            _replace_tokens(root, _scalar_values(analysis, language))
            replacements[name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as destination:
            for item in archive.infolist():
                destination.writestr(item, replacements.get(item.filename, archive.read(item.filename)))
    finally:
        archive.close()
        source.close()
    return output.getvalue()


def _pdf_field_values(analysis: dict[str, Any], language: str) -> dict[str, str]:
    values = _scalar_values(analysis, language)
    labels = LANGUAGE_LABELS[language]
    results = list(analysis.get("results") or [])
    if results:
        values.update(_sample_values(results[0], labels))
    for index, result in enumerate(results, 1):
        for key, value in _sample_values(result, labels).items():
            values[f"sample.{index}.{key.removeprefix('sample.')}"] = value
    return values


def _render_pdf_template(template: bytes, analysis: dict[str, Any], language: str) -> bytes:
    _inspect_pdf_template("template.pdf", template)
    reader = PdfReader(io.BytesIO(template))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    values = _pdf_field_values(analysis, language)
    fields = reader.get_fields() or {}
    for page in writer.pages:
        page_values: dict[str, str] = {}
        for raw_name in fields:
            normalized = _normalized_pdf_field(str(raw_name))
            if normalized in values:
                page_values[str(raw_name)] = values[normalized]
        if page_values:
            writer.update_page_form_field_values(page, page_values, auto_regenerate=True)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _rtf_escape(value: str) -> str:
    output: list[str] = []
    for character in value:
        if character in "\\{}":
            output.append("\\" + character)
        elif ord(character) < 128:
            output.append(character)
        else:
            codepoint = ord(character)
            if codepoint > 0xFFFF:
                encoded = character.encode("utf-16-le")
                units = [int.from_bytes(encoded[index:index + 2], "little") for index in range(0, len(encoded), 2)]
            else:
                units = [codepoint]
            output.extend(f"\\u{unit if unit < 32768 else unit - 65536}?" for unit in units)
    return "".join(output)


def _replace_rtf_tokens(content: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return _rtf_escape(values[key]) if key in values else match.group(0)

    return RTF_TOKEN_PATTERN.sub(replace, content)


def _render_doc_template(template: bytes, analysis: dict[str, Any], language: str) -> bytes:
    _inspect_doc_template("template.doc", template)
    content = _decode_rtf_doc(template)
    labels = LANGUAGE_LABELS[language]
    results = list(analysis.get("results") or [])

    # RTF table rows have a stable \trowd ... \row boundary. Replicate a
    # sample-token row for each result while preserving every RTF style command.
    row_pattern = re.compile(r"(\\trowd\b.*?\\row\b)", re.DOTALL)

    def expand_row(match: re.Match[str]) -> str:
        row = match.group(1)
        if not any(token.startswith(SAMPLE_PREFIX) for token in RTF_TOKEN_PATTERN.findall(row)):
            return row
        return "".join(_replace_rtf_tokens(row, _sample_values(result, labels)) for result in results)

    content = row_pattern.sub(expand_row, content)
    if results:
        content = _replace_rtf_tokens(content, _sample_values(results[0], labels))
    content = _replace_rtf_tokens(content, _scalar_values(analysis, language))
    return content.encode("latin-1")


def render_report_template(filename: str, template: bytes, analysis: dict[str, Any], language: str = "zh") -> bytes:
    if language not in LANGUAGE_LABELS:
        raise ValueError(f"Unsupported export language: {language}")
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "docx":
        return _render_docx_template(template, analysis, language)
    if suffix == "doc":
        return _render_doc_template(template, analysis, language)
    if suffix == "pdf":
        return _render_pdf_template(template, analysis, language)
    raise ValueError("报告模板仅支持 .doc、.docx 或带表单字段的 .pdf 格式。")


def example_report_template(language: str = "zh") -> bytes:
    if language not in LANGUAGE_LABELS:
        raise ValueError(f"Unsupported export language: {language}")
    labels = {
        "zh": ("报告模板示例", "生成时间", "刻度源", "样品结果", "编号", "样品", "质量/g", "Ra/ppm", "Th/ppm", "K/%", "Ra/Bq·kg⁻¹", "Th/Bq·kg⁻¹", "K/Bq·kg⁻¹", "质控"),
        "zht": ("報告範本示例", "產生時間", "刻度源", "樣品結果", "編號", "樣品", "質量/g", "Ra/ppm", "Th/ppm", "K/%", "Ra/Bq·kg⁻¹", "Th/Bq·kg⁻¹", "K/Bq·kg⁻¹", "品管"),
        "en": ("Report template example", "Generated", "Calibration source", "Sample results", "No.", "Sample", "Mass/g", "Ra/ppm", "Th/ppm", "K/%", "Ra/Bq·kg⁻¹", "Th/Bq·kg⁻¹", "K/Bq·kg⁻¹", "QC"),
        "fr": ("Exemple de modèle de rapport", "Généré", "Source d’étalonnage", "Résultats", "N°", "Échantillon", "Masse/g", "Ra/ppm", "Th/ppm", "K/%", "Ra/Bq·kg⁻¹", "Th/Bq·kg⁻¹", "K/Bq·kg⁻¹", "CQ"),
    }[language]
    headers = labels[4:]
    tokens = ("sample.no", "sample.name", "sample.mass_g", "sample.ra_ppm", "sample.th_ppm", "sample.k_percent", "sample.ra_bq_kg", "sample.th_bq_kg", "sample.k_bq_kg", "sample.qc")

    def paragraph(text: str, bold: bool = False) -> str:
        run_props = "<w:rPr><w:b/></w:rPr>" if bold else ""
        return f'<w:p><w:r>{run_props}<w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'

    def cell(text: str, bold: bool = False) -> str:
        return f"<w:tc>{paragraph(text, bold)}</w:tc>"

    header_row = "<w:tr>" + "".join(cell(value, True) for value in headers) + "</w:tr>"
    sample_row = "<w:tr>" + "".join(cell("{{" + token + "}}") for token in tokens) + "</w:tr>"
    body = "".join([
        paragraph("{{report.title}}", True),
        paragraph(f"{labels[1]}：{{{{report.generated_at}}}}"),
        paragraph(f"{labels[2]}：{{{{standard.name}}}} / {{{{standard.calibration_equation}}}}"),
        paragraph("{{method.note}}"),
        paragraph(labels[3], True),
        f"<w:tbl>{header_row}{sample_row}</w:tbl>",
        "<w:sectPr><w:pgSz w:w=\"11906\" w:h=\"16838\"/><w:pgMar w:top=\"1440\" w:right=\"720\" w:bottom=\"1440\" w:left=\"720\"/></w:sectPr>",
    ])
    document = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{WORD_NS}"><w:body>{body}</w:body></w:document>'
    content_types = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''
    relationships = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{REL_NS}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)
    return output.getvalue()


def example_pdf_report_template() -> bytes:
    """Create a fillable PDF example whose AcroForm field names are template tokens."""
    output = io.BytesIO()
    canvas = Canvas(output)
    canvas.setTitle("Ra-Th-K fillable report template")
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(54, 800, "Ra-Th-K Quantitative Report Template")
    canvas.setFont("Helvetica", 9)
    scalar_fields = [
        ("report.title", 760, 250),
        ("report.generated_at", 728, 180),
        ("standard.name", 696, 220),
        ("standard.calibration_equation", 664, 280),
    ]
    for field_name, y, width in scalar_fields:
        canvas.drawString(54, y + 7, field_name)
        canvas.acroForm.textfield(name=field_name, x=220, y=y, width=width, height=22, borderWidth=1)
    headers = ("No.", "Sample", "Mass g", "Ra ppm", "Th ppm", "K %", "QC")
    positions = (54, 94, 214, 274, 334, 394, 454)
    widths = (34, 114, 54, 54, 54, 54, 82)
    canvas.setFont("Helvetica-Bold", 8)
    for x, header in zip(positions, headers):
        canvas.drawString(x, 620, header)
    for row_index, y in enumerate((590, 558, 526), 1):
        fields = (
            f"sample.{row_index}.no", f"sample.{row_index}.name", f"sample.{row_index}.mass_g",
            f"sample.{row_index}.ra_ppm", f"sample.{row_index}.th_ppm", f"sample.{row_index}.k_percent",
            f"sample.{row_index}.qc",
        )
        for x, width, field_name in zip(positions, widths, fields):
            canvas.acroForm.textfield(name=field_name, x=x, y=y, width=width, height=22, borderWidth=1)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(54, 492, "Rename/add AcroForm fields to match the supported tokens shown in the workbench.")
    canvas.save()
    return output.getvalue()
