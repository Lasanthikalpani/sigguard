# Chapter X: RQ3 — Hybrid Integration (QR + AI + Blockchain)

## X.1 Introduction

The integrity of official documents (land deeds, birth certificates, national identity cards, educational credentials) is fundamental to Sri Lanka's public administration. Yet these documents remain vulnerable to signature forgery and content tampering, costing citizens property, identity, and legal standing.

This chapter presents RQ3, which addresses the following research question:

> **How can QR-based cryptographic hashing be effectively integrated with AI verification to create a robust hybrid authentication system with ≥95% tamper detection reliability?**

We extend this with two further questions:

> **Layer 5:** How can QR-based cryptographic hashing distinguish between legitimate amendments and forgeries, while preserving cryptographic integrity?
>
> **Layer 6:** How can QR-based cryptographic hashing distinguish between originals, certified copies, photocopies, and forged copies?

## X.2 Methodology

### X.2.1 Architecture

RQ3 introduces a multi-layer hybrid authentication architecture:

| Layer | Component | Purpose |
|---|---|---|
| Layer 1 | Siamese CNN (RQ1) | Signature forgery detection |
| Layer 2 | Fusion Engine | Weighted AI + crypto decision |
| Layer 3 | QR + SHA-256 + HMAC | Content integrity |
| Layer 4 | RSA signature | Non-repudiation |
| Layer 5 | Document Amendment | Legitimate change management |
| Layer 6 | Copy vs Original | Document type classification |

### X.2.2 Layer 3: QR Code Verification

The QR verification layer implements a 6-step process:

1. **SCAN** — decode QR from document (multi-scale, WeChat + standard detectors)
2. **CONTENT HASH** — recompute SHA-256 of document content (QR region masked)
3. **METADATA HASH** — recompute SHA-256 of (timestamp + issuer + doc_id)
4. **SIGNATURE** — verify HMAC-SHA256 over the integrity record
5. **BLOCKCHAIN** — look up document in append-only ledger
6. **FINAL DECISION** — return one of 4 scenarios

The 4 decision scenarios are:

| Scenario | Status | Trigger |
|---|---|---|
| 1 | `FULLY_AUTHENTIC` | All checks pass |
| 2 | `TAMPERED` | Content hash mismatch |
| 3 | `METADATA_MODIFIED` | Metadata hash mismatch |
| 4 | `AUTHENTIC_NOT_IN_BLOCKCHAIN` | Content valid, ledger miss |

### X.2.3 Layer 5: Document Amendment

Layer 5 addresses a critical gap: **legitimate changes are indistinguishable from forgeries under a pure content-hash scheme**.

When a citizen needs to change their document (e.g., surname after marriage), a **new QR code is issued** with:
- New content hash (reflects new content)
- New metadata hash (reflects new timestamp)
- New HMAC signature
- Blockchain record linking back to the original

The amendment is recorded in the ledger with:
```json
{
  "is_amendment": true,
  "original_doc_id": "LK-1990-00001",
  "amendment_reason": "surname_change",
  "evidence": {"marriage_cert": "MC-2026-001"}
}