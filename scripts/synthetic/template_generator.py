# scripts/synthetic/template_generator.py

import random
from faker import Faker
from dataclasses import dataclass
import json
from datetime import datetime
import os
from PIL import Image, ImageDraw

fake_si = Faker('en_US')
fake_ta = Faker('en_US')

SINHALA_FIRST = ["Chandrasekara", "Wickramasinghe", "Perera", "Fernando", "Jayasuriya", "Dissanayake", "Rathnayake", "Gunawardena"]
TAMIL_FIRST = ["Sivalingam", "Kumaraswamy", "Rajendran", "Thuraisingham", "Sivakumar", "Balasubramaniam"]
ENGLISH_FIRST = ["Silva", "De Silva", "Peiris", "Mendis", "Cooray"]
DISTRICTS = ["Colombo", "Matara", "Anuradhapura", "Kandy", "Galle", "Jaffna", "Kurunegala", "Ratnapura"]

@dataclass
class DocumentRecord:
    document_id: str
    document_type: str
    script: str
    name: str
    dob: str
    district: str
    issuer: str
    issued_at: str
    content_text: str
    signature_image_path: str

def generate_birth_cert(script: str, idx: int) -> DocumentRecord:
    if script == "sinhala":
        name = f"{random.choice(SINHALA_FIRST)} {random.choice(SINHALA_FIRST)}"
    elif script == "tamil":
        name = f"{random.choice(TAMIL_FIRST)} {random.choice(TAMIL_FIRST)}"
    else:
        name = f"{random.choice(ENGLISH_FIRST)} {random.choice(ENGLISH_FIRST)}"
    
    dob = f"{random.randint(1950, 2020)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
    district = random.choice(DISTRICTS)
    doc_id = f"BC-{random.randint(1950,2026)}-{idx:06d}"
    
    content = (f"Birth Certificate: {doc_id}\nName: {name}\nDOB: {dob}\nPlace: {district}\nRegistrar General's Office")
    
    return DocumentRecord(
        document_id=doc_id,
        document_type="BIRTH_CERTIFICATE",
        script=script,
        name=name,
        dob=dob,
        district=district,
        issuer="Registrar General's Office",
        issued_at=f"{random.randint(1950,2026)}-{random.randint(1,12):02d}-15T10:30:00Z",
        content_text=content,
        signature_image_path=f"signatures/{script}/sig_{idx:06d}.png"
    )

# මෙය අනිවාර්යයෙන්ම තිබිය යුතුය (ledger_writer.py මෙය අපේක්ෂා කරයි)
def generate_document(document_type: str, idx: int, script: str = "sinhala") -> dict:
    """Generate a single synthetic document record as a dict."""
    if document_type == "BIRTH_CERTIFICATE":
        record = generate_birth_cert(script, idx)
        return record.__dict__
    
    # Fallback for other types
    doc_id = f"{document_type[:2].upper()}-2026-{idx:06d}"
    return {
        "document_id": doc_id,
        "document_type": document_type,
        "script": script,
        "issuer": "Registrar General's Office",
        "issued_at": datetime.utcnow().isoformat() + "Z",
        "content_text": f"Document {doc_id} - Placeholder Content",
        "rendered_image_path": f"data/rq3_dataset/documents/{document_type.lower()}/{doc_id}.png",
    }
