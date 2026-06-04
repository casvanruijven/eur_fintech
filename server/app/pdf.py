"""Render a Receipt into a clean document (PDF or PNG).

This is where ZZPay's core promise becomes tangible: structured receipt data ->
a polished, shareable artifact. We render an HTML template with Jinja2, let
xhtml2pdf produce the PDF, and rasterise page 1 of that PDF to PNG with pypdfium2.

Both libraries are pure-Python / self-contained wheels, so no native GTK/Pango
libraries are required — the app renders out of the box on Windows.
"""

import io
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models import CreditNote, Receipt

_TEMPLATES = Path(__file__).resolve().parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=select_autoescape(["html"]),
)


_CHANNEL_LABELS = {"NFC": "NFC tap", "ONLINE_LINK": "Online link"}


def _render_html(receipt: Receipt) -> str:
    template = _env.get_template("receipt.html")
    return template.render(
        invoice_id=receipt.invoice_id,
        supplier_name=receipt.supplier_name,
        supplier_vat=receipt.supplier_vat,
        supplier_address=receipt.supplier_address,
        issue_date=receipt.issue_date,
        issue_time=receipt.issue_time,
        channel_label=_CHANNEL_LABELS.get(receipt.channel, receipt.channel),
        currency=receipt.currency,
        line_items=receipt.invoice_lines or [],
        line_extension_amount=receipt.line_extension_amount,
        tax_total=receipt.tax_total,
        payable_amount=receipt.payable_amount,
        status=receipt.status,
        credit_note_id=receipt.credit_note_id,
    )


def _render_cn_html(cn: CreditNote, original: Receipt) -> str:
    template = _env.get_template("credit_note.html")
    return template.render(
        credit_note_id=cn.credit_note_id,
        original_receipt_id=cn.original_receipt_id,
        supplier_name=original.supplier_name,
        supplier_vat=original.supplier_vat,
        issue_date=cn.issue_date,
        issue_time=cn.issue_time,
        currency=cn.currency,
        line_items=cn.credited_items or [],
        line_extension_amount=cn.line_extension_amount,
        tax_total=cn.tax_total,
        payable_amount=cn.payable_amount,
        reason=cn.reason,
        status=cn.status,
    )


def _pdf_from_html(html: str) -> bytes:
    # Imported lazily so importing this module stays cheap for non-render code
    # paths (e.g. the test suite, which skips the binary endpoints).
    from xhtml2pdf import pisa

    out = io.BytesIO()
    result = pisa.CreatePDF(src=html, dest=out, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"PDF rendering failed ({result.err} error(s))")
    return out.getvalue()


def render_pdf(receipt: Receipt) -> bytes:
    return _pdf_from_html(_render_html(receipt))


def render_credit_note_pdf(cn: CreditNote, original: Receipt) -> bytes:
    return _pdf_from_html(_render_cn_html(cn, original))


def _png_from_pdf(pdf_bytes: bytes, scale: float = 3.0) -> bytes:
    # PNG is the same document rasterised: draw page 1 to a bitmap with pypdfium2
    # and trim the surrounding page margin so the image hugs the document instead
    # of carrying the full (tall) page whitespace.
    import pypdfium2 as pdfium
    from PIL import Image, ImageChops

    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        image = pdf[0].render(scale=scale).to_pil().convert("RGB")
    finally:
        pdf.close()

    background = Image.new("RGB", image.size, (255, 255, 255))
    bbox = ImageChops.difference(image, background).getbbox()
    if bbox:
        pad = int(4 * scale)
        left, top, right, bottom = bbox
        image = image.crop(
            (
                max(left - pad, 0),
                max(top - pad, 0),
                min(right + pad, image.width),
                min(bottom + pad, image.height),
            )
        )

    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def render_png(receipt: Receipt, scale: float = 3.0) -> bytes:
    return _png_from_pdf(render_pdf(receipt), scale)


def render_credit_note_png(cn: CreditNote, original: Receipt, scale: float = 3.0) -> bytes:
    return _png_from_pdf(render_credit_note_pdf(cn, original), scale)


def receipt_filename(receipt: Receipt, ext: str) -> str:
    # invoice_id is unique and filesystem-safe (e.g. "ZZP-2026-0001").
    return f"zzpay-{receipt.invoice_id}.{ext}"


def credit_note_filename(cn: CreditNote, ext: str) -> str:
    return f"zzpay-{cn.credit_note_id}.{ext}"


def download_headers(filename: str) -> dict:
    """Attachment headers for an export. ``no-store`` is important: exports are
    rendered live from the current data, so after a refund/email the browser must
    re-fetch a fresh document instead of serving a stale cached copy."""
    return {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store",
    }
