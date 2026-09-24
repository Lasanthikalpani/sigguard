"""SigGuard FastAPI service (RQ1, industry-level)."""
import io
import time
import os
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel, Field

from src.models.siamese import SiameseNetwork
from src.data.preprocess import SignaturePreprocessor
from src.api.routes import benchmark

state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting SigGuard API...")
    model = SiameseNetwork(embedding_dim=128, backbone="resnet18")
    model.eval()

    try:
        checkpoint = torch.load(
            "models/checkpoints/sigguard_v2/best_model.pth",
            map_location="cpu",
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        print("Model checkpoint loaded")
    except FileNotFoundError:
        print("No checkpoint found, using random weights")

    state["model"] = model
    state["preprocessor"] = SignaturePreprocessor(target_size=(224, 224))
    state["device"] = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(state["device"])

    print(f"SigGuard API ready on {state['device']}")
    yield
    print("Shutting down SigGuard API...")


app = FastAPI(
    title="SigGuard API",
    description="AI-Powered Signature Forgery Detection for Sri Lankan Government Documents",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Benchmark router
app.include_router(benchmark.router)

class VerificationResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    verdict: str = Field(..., description="'genuine' or 'forged'")
    confidence: float = Field(..., ge=0.0, le=1.0)
    distance: float
    inference_time_ms: float
    model_version: str = "1.0.0"


class HealthResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    status: str
    model_loaded: bool
    device: str
    version: str = "1.0.0"


@app.get("/", tags=["root"])
async def root():
    return {
        "name": "SigGuard API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health():
    return HealthResponse(
        status="healthy",
        model_loaded="model" in state,
        device=str(state.get("device", "unknown")),
    )


@app.post("/verify", response_model=VerificationResponse, tags=["verification"])
async def verify_signature(
    reference: UploadFile = File(..., description="Reference genuine signature"),
    test: UploadFile = File(..., description="Signature to verify"),
):
    if "model" not in state:
        raise HTTPException(status_code=503, detail="Model not loaded")

    start = time.time()

    try:
        ref_bytes = await reference.read()
        test_bytes = await test.read()

        ref_img = Image.open(io.BytesIO(ref_bytes)).convert("L")
        test_img = Image.open(io.BytesIO(test_bytes)).convert("L")

        ref_path = "temp_ref.png"
        test_path = "temp_test.png"
        ref_img.save(ref_path)
        test_img.save(test_path)

        preprocessor = state["preprocessor"]
        ref_processed = preprocessor(ref_path)
        test_processed = preprocessor(test_path)

        ref_tensor = (
            torch.from_numpy(ref_processed)
            .unsqueeze(0).unsqueeze(0).repeat(1, 3, 1, 1)
            .to(state["device"])
        )
        test_tensor = (
            torch.from_numpy(test_processed)
            .unsqueeze(0).unsqueeze(0).repeat(1, 3, 1, 1)
            .to(state["device"])
        )

        model = state["model"]
        with torch.no_grad():
            emb1, emb2 = model(ref_tensor, test_tensor)
            distance = torch.nn.functional.pairwise_distance(emb1, emb2).item()

        threshold = 0.1358
        verdict = "genuine" if distance < threshold else "forged"
        confidence = max(0.0, min(1.0, 1.0 - distance))
        inference_time = (time.time() - start) * 1000

        os.remove(ref_path)
        os.remove(test_path)

        return VerificationResponse(
            verdict=verdict,
            confidence=confidence,
            distance=distance,
            inference_time_ms=inference_time,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")