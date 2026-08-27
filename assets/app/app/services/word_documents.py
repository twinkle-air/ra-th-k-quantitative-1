from __future__ import annotations

from io import BytesIO
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from xml.etree import ElementTree


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _split_text_line(text: str) -> list[object]:
    text = text.strip()
    if not text:
        return []
    if "=" in text and not re.match(r"^[-+]?\d", text):
        return [text]
    return [part for part in re.split(r"[\t,;，]+|\s{2,}", text) if part.strip()]


def _docx_rows(payload: bytes) -> list[list[object]]:
    try:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
    except (KeyError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise ValueError("DOCX 文件结构损坏或不是有效的 Word 文档。") from exc
    body = root.find(f"{_W}body")
    rows: list[list[object]] = []
    if body is None:
        return rows

    def paragraph_text(paragraph: ElementTree.Element) -> str:
        parts: list[str] = []
        for node in paragraph.iter():
            if node.tag == f"{_W}t":
                parts.append(node.text or "")
            elif node.tag == f"{_W}tab":
                parts.append("\t")
            elif node.tag in {f"{_W}br", f"{_W}cr"}:
                parts.append("\n")
        return "".join(parts)

    for child in body:
        if child.tag == f"{_W}p":
            for line in paragraph_text(child).splitlines():
                row = _split_text_line(line)
                if row:
                    rows.append(row)
        elif child.tag == f"{_W}tbl":
            for table_row in child.iter(f"{_W}tr"):
                cells = []
                for cell in table_row.findall(f"{_W}tc"):
                    value = " ".join(paragraph_text(paragraph).strip()
                                     for paragraph in cell.findall(f"{_W}p")).strip()
                    cells.append(value)
                if any(cells):
                    rows.append(cells)
    return rows


def _rtf_rows(payload: bytes) -> list[list[object]] | None:
    if not payload.lstrip().startswith(b"{\\rtf"):
        return None
    text = payload.decode("latin-1", errors="replace")
    text = re.sub(r"\\u(-?\d+)\??", lambda m: chr(int(m.group(1)) % 65536), text)
    text = re.sub(r"\\(?:par|line|row)\b", "\n", text)
    text = re.sub(r"\\tab\b", "\t", text)
    text = re.sub(r"\\'[0-9a-fA-F]{2}", "", text)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?|[{}]", "", text)
    return [row for line in text.splitlines() if (row := _split_text_line(line))]


def _convert_binary_doc(payload: bytes) -> bytes:
    failure_detail = ""
    with tempfile.TemporaryDirectory(prefix="rtk-doc-") as directory:
        source = Path(directory) / "input.doc"
        destination = Path(directory) / "output.docx"
        source.write_bytes(payload)
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if soffice:
            completed = subprocess.run(
                [soffice, "--headless", "--convert-to", "docx", "--outdir", directory, str(source)],
                capture_output=True, timeout=45, check=False,
            )
            converted = Path(directory) / "input.docx"
            if completed.returncode == 0 and converted.exists():
                return converted.read_bytes()
        if shutil.which("powershell.exe"):
            script = (
                "$ErrorActionPreference='Stop';$app=$null;$doc=$null;"
                "try{try{$app=New-Object -ComObject Word.Application}catch{$app=New-Object -ComObject KWPS.Application};"
                "$app.Visible=$false;$doc=$app.Documents.Open($env:RTK_DOC_SOURCE);"
                "try{$doc.SaveAs2($env:RTK_DOC_DEST,16)}catch{$doc.SaveAs($env:RTK_DOC_DEST,16)}}"
                "finally{if($doc){$doc.Close($false)};if($app){$app.Quit()}}"
            )
            environment = os.environ.copy()
            environment.update({"RTK_DOC_SOURCE": str(source), "RTK_DOC_DEST": str(destination)})
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, timeout=45, check=False, env=environment,
            )
            if completed.returncode == 0 and destination.exists():
                return destination.read_bytes()
            failure_detail = (completed.stderr or completed.stdout).decode(errors="replace").strip()[:300]
    suffix = f" 转换器信息：{failure_detail}" if failure_detail else ""
    raise ValueError(f"无法读取二进制 .doc；请安装 Word/WPS 或 LibreOffice，或另存为 .docx。{suffix}")


def read_word_rows(filename: str, payload: bytes) -> list[list[object]]:
    extension = Path(filename).suffix.lower()
    if extension == ".docx" or payload.startswith(b"PK\x03\x04"):
        return _docx_rows(payload)
    if extension != ".doc":
        raise ValueError("Word 文件仅支持 .doc 和 .docx。")
    rtf = _rtf_rows(payload)
    return rtf if rtf is not None else _docx_rows(_convert_binary_doc(payload))


def read_word_text(filename: str, payload: bytes) -> str:
    return "\n".join(" : ".join(str(cell).strip() for cell in row if str(cell).strip())
                      for row in read_word_rows(filename, payload))
