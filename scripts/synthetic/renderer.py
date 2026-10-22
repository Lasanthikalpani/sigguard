# scripts/synthetic/renderer.py
"""
Layer A — Document Renderer
- Renders document templates as images (300/600 DPI)
- Overlays signature onto the signature region
"""

import os
from PIL import Image, ImageDraw, ImageFont
from template_generator import DocumentRecord


# --------------------------------------------------------------
# 1. Render the document body (without signature)
# --------------------------------------------------------------
def render_document(record: DocumentRecord, output_path: str) -> Image.Image:
    """Render a document as an A4 image (300 DPI)."""
    img = Image.new("RGB", (2480, 3508), color="white")  # A4 @ 300 DPI
    draw = ImageDraw.Draw(img)

    # Pick font based on script
    if record.script == "sinhala":
        header_font = ImageFont.truetype("fonts/NotoSansSinhala-Bold.ttf", 60)
        body_font   = ImageFont.truetype("fonts/NotoSansSinhala-Regular.ttf", 36)
    elif record.script == "tamil":
        header_font = ImageFont.truetype("fonts/NotoSansTamil-Bold.ttf", 60)
        body_font   = ImageFont.truetype("fonts/NotoSansTamil-Regular.ttf", 36)
    else:
        header_font = ImageFont.truetype("fonts/DejaVuSans-Bold.ttf", 60)
        body_font   = ImageFont.truetype("fonts/DejaVuSans.ttf", 36)

    # Header
    draw.text((200, 200), "Democratic Socialist Republic of Sri Lanka",
              fill="black", font=header_font)
    draw.text((200, 300), record.document_type.replace("_", " "),
              fill="black", font=header_font)

    # Body
    y = 500
    for line in record.content_text.split("\n"):
        draw.text((200, y), line, fill="black", font=body_font)
        y += 60

    # Signature placeholder (will be overlaid later)
    draw.rectangle([(1800, 2800), (2300, 3100)], outline="gray", width=2)
    draw.text((1850, 2850), "Signature", fill="gray", font=body_font)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, dpi=(300, 300))
    return img


# --------------------------------------------------------------
# 2. Overlay signature onto the document   ← 3.4 මෙහි!
# --------------------------------------------------------------
def overlay_signature(doc_image: Image.Image,
                      sig_image: Image.Image,
                      position: tuple = (1800, 2800)) -> Image.Image:
    """
    Paste a signature image onto the document's signature region.

    Args:
        doc_image : the rendered document (PIL Image, RGB)
        sig_image : the generated signature (PIL Image, mode 'L')
        position  : top-left (x, y) of the signature box

    Returns:
        A new document image with the signature overlaid.
    """
    # Resize signature to fit region (500 x 300)
    sig_resized = sig_image.resize((500, 300), Image.LANCZOS)

    # Convert to RGBA so white background becomes transparent
    sig_rgba = sig_resized.convert("RGBA")
    data = sig_rgba.getdata()
    new_data = [
        (255, 255, 255, 0) if item[0] > 200 else (item[0], item[0], item[0], 255)
        for item in data
    ]
    sig_rgba.putdata(new_data)

    # Paste onto the document using the alpha channel as a mask
    out = doc_image.copy()
    out.paste(sig_rgba, position, sig_rgba)
    return out


# --------------------------------------------------------------
# 3. Convenience wrapper — render + overlay in one call
# --------------------------------------------------------------
def render_with_signature(record: DocumentRecord,
                          signature_path: str,
                          output_path: str) -> Image.Image:
    """Render the document and overlay the signature in one step."""
    doc = render_document(record, output_path)
    sig = Image.open(signature_path).convert("L")
    final = overlay_signature(doc, sig)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final.save(output_path, dpi=(300, 300))
    return final