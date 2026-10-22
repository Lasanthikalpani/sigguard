# scripts/synthetic/tamper_generator.py

from PIL import Image, ImageDraw, ImageFont

def tamper_content(doc_image: Image.Image, tamper_type: str) -> Image.Image:
    """6 tamper types from RQ3 test cases."""
    img = doc_image.copy()
    draw = ImageDraw.Draw(img)
    
    if tamper_type == "dob_change":
        # DOB 1990 → 1995
        draw.rectangle([(600, 700), (1400, 760)], fill="white")
        draw.text((600, 700), "DOB: 1995-01-15", fill="black",
                  font=ImageFont.truetype("fonts/DejaVuSans.ttf", 36))
    
    elif tamper_type == "name_change":
        # Change surname
        draw.rectangle([(600, 620), (1400, 680)], fill="white")
        draw.text((600, 620), "Name: Fernando Perera", fill="black",
                  font=ImageFont.truetype("fonts/DejaVuSans.ttf", 36))
    
    elif tamper_type == "amount_change":
        # Land deed: extent 10 → 100 perch
        draw.rectangle([(600, 800), (1400, 860)], fill="white")
        draw.text((600, 800), "Extent: 100 perches", fill="black",
                  font=ImageFont.truetype("fonts/DejaVuSans.ttf", 36))
    
    elif tamper_type == "qr_replacement":
        # Replace QR with a fake QR (different hashes)
        qr_region = img.crop((2000, 200, 2300, 500))
        img.paste(qr_region.transpose(Image.FLIP_LEFT_RIGHT), (2000, 200))
    
    elif tamper_type == "signature_copy":
        # Copy another signer's signature into this doc
        other_sig = Image.open("signatures/sinhala/genuine/signer9999_g0.png")
        img.paste(other_sig.resize((500, 300)), (1800, 2800))
    
    elif tamper_type == "cut_paste":
        # Cut a region and paste elsewhere
        region = img.crop((200, 500, 800, 700))
        img.paste(region, (1500, 2000))
    
    return img