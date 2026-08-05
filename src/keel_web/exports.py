"""Single-sheet .xlsx export for admin list views — stdlib only.

An admin table that can be filtered is worth exporting *as filtered*, and the
format people actually want is Excel, not CSV. This writes the minimum valid
OOXML package by hand (zipfile + a few XML parts) so no host has to take on
openpyxl/xlsxwriter for what is, in the end, one flat grid.

Deliberately ONE sheet: an export is a working table people sort, filter and
paste elsewhere, and splitting it across sheets breaks every one of those. Rows
land in the order the caller yields them.

    return xlsx_response("plans.xlsx", ["Title", "Volume"], rows)

``rows`` may be any iterable of sequences; it is consumed once. Cell values are
written as numbers when they are int/float (so Excel sums them) and as inline
strings otherwise — inline strings avoid a sharedStrings part entirely, which
keeps the writer streaming-friendly and the package small.
"""

from __future__ import annotations

import datetime as _dt
import io
import re
import zipfile

from django.http import HttpResponse

__all__ = ["write_xlsx", "xlsx_response"]

_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# Excel rejects most C0 control characters outright — a single stray \x0b in a
# text field makes the whole workbook unopenable, so they are stripped, not escaped.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# Header row bold (style 1); everything else default (style 0).
_STYLES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<styleSheet xmlns="{_NS}">'
    '<fonts count="2">'
    '<font><sz val="11"/><name val="Calibri"/></font>'
    '<font><b/><sz val="11"/><name val="Calibri"/></font>'
    "</fonts>"
    '<fills count="2">'
    '<fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill>'
    "</fills>"
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="2">'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
    "</cellXfs>"
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
    "</styleSheet>"
)


def _esc(text: str) -> str:
    return (
        _CONTROL_CHARS.sub("", str(text))
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _col_letter(idx0: int) -> str:
    idx, out = idx0 + 1, ""
    while idx:
        idx, rem = divmod(idx - 1, 26)
        out = chr(ord("A") + rem) + out
    return out


def _cell(col0: int, row: int, value, style: int) -> str:
    ref = f"{_col_letter(col0)}{row}"
    if isinstance(value, bool):  # bool is an int subclass — check it first
        value = "Yes" if value else "No"
    elif value is None:
        value = ""
    elif isinstance(value, (_dt.datetime, _dt.date)):
        value = value.isoformat(sep=" ", timespec="minutes") if isinstance(
            value, _dt.datetime
        ) else value.isoformat()
    if isinstance(value, (int, float)):
        return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'
    return (
        f'<c r="{ref}" s="{style}" t="inlineStr">'
        f'<is><t xml:space="preserve">{_esc(value)}</t></is></c>'
    )


def write_xlsx(headers, rows, *, sheet_name="Export", widths=None) -> bytes:
    """Return one .xlsx workbook (a single sheet) as bytes.

    ``widths`` is an optional list of column widths in characters, positionally
    matched to ``headers``; missing entries fall back to Excel's default.
    """
    headers = list(headers)
    body = []
    for r, row in enumerate(rows, start=2):
        body.append(
            f'<row r="{r}">'
            + "".join(_cell(c, r, v, 0) for c, v in enumerate(row))
            + "</row>"
        )
        if r > 1_048_576:
            raise ValueError("export exceeds Excel's 1,048,576-row limit")

    head = (
        '<row r="1">'
        + "".join(_cell(c, 1, h, 1) for c, h in enumerate(headers))
        + "</row>"
    )
    last = f"{_col_letter(max(len(headers) - 1, 0))}{len(body) + 1}"

    cols = ""
    if widths:
        cols = (
            "<cols>"
            + "".join(
                f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>'
                for i, w in enumerate(widths)
                if w
            )
            + "</cols>"
        )

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="{_NS}">'
        f'<dimension ref="A1:{last}"/>'
        # Freeze the header and turn on the filter dropdowns: this table exists to
        # be scanned, and both are what a reader reaches for first.
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        "</sheetView></sheetViews>"
        '<sheetFormatPr defaultRowHeight="15"/>'
        f"{cols}"
        f"<sheetData>{head}{''.join(body)}</sheetData>"
        f'<autoFilter ref="A1:{last}"/>'
        "</worksheet>"
    )

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<workbook xmlns="{_NS}" xmlns:r="{_REL_NS}">'
        f'<sheets><sheet name="{_esc(sheet_name)[:31]}" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{_REL_NS}/worksheet" Target="worksheets/sheet1.xml"/>'
        f'<Relationship Id="rId2" Type="{_REL_NS}/styles" Target="styles.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{_REL_NS}/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/styles.xml", _STYLES_XML)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()


def xlsx_response(filename, headers, rows, *, sheet_name="Export", widths=None):
    """``write_xlsx`` wrapped in a download response."""
    payload = write_xlsx(headers, rows, sheet_name=sheet_name, widths=widths)
    response = HttpResponse(
        payload,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Content-Length"] = str(len(payload))
    return response
