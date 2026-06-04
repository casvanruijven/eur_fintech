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

from app.models import Receipt

_TEMPLATES = Path(__file__).resolve().parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=select_autoescape(["html"]),
)


def _render_html(receipt: Receipt) -> str:
    items = receipt.line_items or []
    subtotal = float(receipt.total_amount) - float(receipt.vat_amount)
    template = _env.get_template("receipt.html")
    return template.render(
        receipt_id=str(receipt.id)[:8],
        merchant_name=receipt.merchant_name,
        merchant_vat=receipt.merchant_vat,
        purchased_at=receipt.purchased_at.strftime("%d-%m-%Y %H:%M"),
        currency=receipt.currency,
        line_items=items,
        subtotal=subtotal,
        vat_amount=receipt.vat_amount,
        total_amount=receipt.total_amount,
    )


def render_pdf(receipt: Receipt) -> bytes:
    # Imported lazily so importing this module stays cheap for non-render code
    # paths (e.g. the test suite, which skips the binary endpoints).
    from xhtml2pdf import pisa

    out = io.BytesIO()
    result = pisa.CreatePDF(src=_render_html(receipt), dest=out, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"PDF rendering failed ({result.err} error(s))")
    return out.getvalue()


def render_png(receipt: Receipt, scale: float = 3.0) -> bytes:
    # PNG is the same document rasterised: render to PDF, then draw page 1 to a
    # bitmap with pypdfium2 and trim the surrounding page margin so the image
    # hugs the receipt instead of carrying the full (tall) page whitespace.
    import pypdfium2 as pdfium
    from PIL import Image, ImageChops

    pdf = pdfium.PdfDocument(render_pdf(receipt))
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


def receipt_filename(receipt: Receipt, ext: str) -> str:
    safe_merchant = "".join(c for c in receipt.merchant_name if c.isalnum() or c in " -_").strip()
    date = receipt.purchased_at.strftime("%Y%m%d")
    return f"zzpay-{safe_merchant or 'bon'}-{date}.{ext}".replace(" ", "_")
