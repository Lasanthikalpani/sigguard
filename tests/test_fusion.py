"""Unit tests for RQ3 FusionEngine."""
import pytest

from src.api.services.fusion_engine import (
    FusionEngine,
    FusionResult,
    PATH_AUTHENTIC,
    PATH_CRYPTO_TAMPER,
    PATH_AI_SUSPICIOUS,
    PATH_LOW_CONFIDENCE,
)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def engine():
    """Default fusion engine."""
    return FusionEngine()


@pytest.fixture
def ai_pass():
    """AI result: pass (high similarity)."""
    return {"similarity": 0.94, "prediction": "genuine"}


@pytest.fixture
def ai_fail():
    """AI result: fail (low similarity)."""
    return {"similarity": 0.60, "prediction": "forged"}


@pytest.fixture
def crypto_pass():
    """Crypto result: all valid."""
    return {
        "hmac_valid": True,
        "document_match": True,
        "timestamp_valid": True,
    }


@pytest.fixture
def crypto_hmac_fail():
    """Crypto result: HMAC invalid (QR tampered)."""
    return {
        "hmac_valid": False,
        "document_match": True,
        "timestamp_valid": True,
    }


@pytest.fixture
def crypto_doc_fail():
    """Crypto result: document hash mismatch (content tampered)."""
    return {
        "hmac_valid": True,
        "document_match": False,
        "timestamp_valid": True,
    }


@pytest.fixture
def crypto_total_fail():
    """Crypto result: everything invalid."""
    return {
        "hmac_valid": False,
        "document_match": False,
        "timestamp_valid": False,
    }


# ============================================================
# CRYPTO SCORE COMPUTATION
# ============================================================

def test_crypto_score_all_valid(engine, crypto_pass):
    """All valid → score 1.0."""
    assert engine.compute_crypto_score(crypto_pass) == 1.0


def test_crypto_score_hmac_fail(engine, crypto_hmac_fail):
    """HMAC fail → score 0.5 (doc + ts only)."""
    assert engine.compute_crypto_score(crypto_hmac_fail) == 0.5


def test_crypto_score_doc_fail(engine, crypto_doc_fail):
    """Doc mismatch → score 0.6 (hmac + ts)."""
    assert engine.compute_crypto_score(crypto_doc_fail) == 0.6


def test_crypto_score_total_fail(engine, crypto_total_fail):
    """All fail → score 0.0."""
    assert engine.compute_crypto_score(crypto_total_fail) == 0.0


# ============================================================
# FUSION DECISION PATHS
# ============================================================

def test_fusion_hybrid_authentic(engine, ai_pass, crypto_pass):
    """Both pass → HYBRID_AUTHENTIC."""
    result = engine.fuse(ai_pass, crypto_pass)
    
    assert result.is_authentic is True
    assert result.tamper_detected is False
    assert result.decision_path == PATH_AUTHENTIC
    assert result.ai_score == 0.94
    assert result.crypto_score == 1.0
    assert result.confidence >= 0.95


def test_fusion_crypto_tamper_hard_constraint(engine, ai_pass, crypto_hmac_fail):
    """Crypto fail → CRYPTO_TAMPER (bypasses AI even if AI passes)."""
    result = engine.fuse(ai_pass, crypto_hmac_fail)
    
    assert result.is_authentic is False
    assert result.tamper_detected is True
    assert result.decision_path == PATH_CRYPTO_TAMPER
    # AI passed but crypto overrides
    assert result.ai_score == 0.94
    assert result.crypto_score == 0.5


def test_fusion_crypto_tamper_with_ai_fail(engine, ai_fail, crypto_total_fail):
    """Crypto fail → CRYPTO_TAMPER (crypto has priority)."""
    result = engine.fuse(ai_fail, crypto_total_fail)
    
    assert result.is_authentic is False
    assert result.tamper_detected is True
    assert result.decision_path == PATH_CRYPTO_TAMPER


def test_fusion_ai_suspicious(engine, ai_fail, crypto_pass):
    """AI fail → AI_SUSPICIOUS (crypto passes but AI does not)."""
    result = engine.fuse(ai_fail, crypto_pass)
    
    assert result.is_authentic is False
    assert result.tamper_detected is False
    assert result.decision_path == PATH_AI_SUSPICIOUS


def test_fusion_low_confidence(engine, crypto_pass):
    """
    Both thresholds pass but combined below fusion threshold.
    This is defensive; with default weights it's hard to hit.
    """
    # Custom engine with very high fusion threshold
    strict_engine = FusionEngine(
        ai_weight=0.5, crypto_weight=0.5,
        ai_threshold=0.5, crypto_threshold=0.5,
        fusion_threshold=0.99,  # impossible to reach
    )
    ai = {"similarity": 0.85, "prediction": "genuine"}
    result = strict_engine.fuse(ai, crypto_pass)
    
    assert result.is_authentic is False
    assert result.tamper_detected is False
    assert result.decision_path == PATH_LOW_CONFIDENCE


# ============================================================
# EXPLANATIONS
# ============================================================

def test_explanations_structure(engine, ai_pass, crypto_pass):
    """Explanations dict contains required fields."""
    result = engine.fuse(ai_pass, crypto_pass)
    exp = result.explanations
    
    # Top-level keys
    assert "weights" in exp
    assert "thresholds" in exp
    assert "ai_breakdown" in exp
    assert "crypto_breakdown" in exp
    assert "combined_confidence" in exp
    assert "components_passed" in exp
    
    # AI breakdown
    assert exp["ai_breakdown"]["similarity"] == 0.94
    assert exp["ai_breakdown"]["weighted_contribution"] == 0.376  # 0.4 * 0.94
    
    # Crypto breakdown
    assert exp["crypto_breakdown"]["score"] == 1.0
    assert exp["crypto_breakdown"]["hmac_valid"] is True
    assert exp["crypto_breakdown"]["document_match"] is True
    assert exp["crypto_breakdown"]["weighted_contribution"] == 0.6


# ============================================================
# CONFIDENCE CALCULATION
# ============================================================

def test_confidence_weighted_sum(engine, ai_pass, crypto_pass):
    """Confidence = 0.4 * AI + 0.6 * Crypto."""
    result = engine.fuse(ai_pass, crypto_pass)
    expected = 0.4 * 0.94 + 0.6 * 1.0  # = 0.976
    assert result.confidence == pytest.approx(expected, abs=1e-4)


def test_confidence_with_different_weights():
    """Custom weights change confidence."""
    engine = FusionEngine(ai_weight=0.7, crypto_weight=0.3)
    ai = {"similarity": 0.90}
    crypto = {"hmac_valid": True, "document_match": True, "timestamp_valid": True}
    
    result = engine.fuse(ai, crypto)
    expected = 0.7 * 0.90 + 0.3 * 1.0  # = 0.93
    assert result.confidence == pytest.approx(expected, abs=1e-4)


# ============================================================
# WEIGHT VALIDATION
# ============================================================

def test_weights_must_sum_to_one():
    """Invalid weight sum raises ValueError."""
    with pytest.raises(ValueError, match="sum to 1.0"):
        FusionEngine(ai_weight=0.5, crypto_weight=0.4)


def test_update_weights(engine):
    """update_weights changes both."""
    engine.update_weights(ai_weight=0.6, crypto_weight=0.4)
    assert engine.ai_weight == 0.6
    assert engine.crypto_weight == 0.4


def test_update_weights_invalid(engine):
    """Invalid update raises."""
    with pytest.raises(ValueError):
        engine.update_weights(ai_weight=0.7, crypto_weight=0.7)


# ============================================================
# THRESHOLD CALIBRATION (RQ3 TARGET: >=95% TAMPER DETECTION)
# ============================================================

def test_threshold_calibration_achieves_95_percent(engine):
    """
    RQ3 KEY TEST: Calibration should achieve >=95% TPR on
    simulated validation data.
    """
    # Simulate 100 samples: 50 tampered, 50 clean
    import random
    random.seed(42)
    np_seed = 42
    import numpy as np
    np.random.seed(np_seed)
    
    validation = []
    # Tampered samples: crypto fails → low combined score
    for _ in range(50):
        crypto_fail = {"hmac_valid": False, "document_match": False, "timestamp_valid": True}
        ai = {"similarity": np.random.uniform(0.2, 0.5)}
        result = engine.fuse(ai, crypto_fail)
        validation.append({
            "is_tampered": True,
            "combined_score": result.confidence,
        })
    # Clean samples: everything passes → high combined
    for _ in range(50):
        crypto_ok = {"hmac_valid": True, "document_match": True, "timestamp_valid": True}
        ai = {"similarity": np.random.uniform(0.90, 0.99)}
        result = engine.fuse(ai, crypto_ok)
        validation.append({
            "is_tampered": False,
            "combined_score": result.confidence,
        })
    
    cal = engine.calibrate_thresholds(validation, target_tpr=0.95)
    
    assert "optimal_threshold" in cal
    assert cal["achieved_tpr"] >= 0.95, (
        f"TPR {cal['achieved_tpr']} below 95%"
    )
    assert cal["n_samples"] == 100
    assert cal["n_tampered"] == 50
    assert cal["n_clean"] == 50


def test_calibration_empty_data(engine):
    """Empty validation data returns error dict."""
    cal = engine.calibrate_thresholds([])
    assert "error" in cal


# ============================================================
# DETERMINISM
# ============================================================

def test_fusion_deterministic(engine, ai_pass, crypto_pass):
    """Same input → same output (no randomness)."""
    r1 = engine.fuse(ai_pass, crypto_pass)
    r2 = engine.fuse(ai_pass, crypto_pass)
    
    assert r1.is_authentic == r2.is_authentic
    assert r1.confidence == r2.confidence
    assert r1.decision_path == r2.decision_path


# ============================================================
# EDGE CASES
# ============================================================

def test_fusion_missing_ai_similarity(engine, crypto_pass):
    """Missing AI similarity defaults to 0.0."""
    result = engine.fuse({}, crypto_pass)
    assert result.ai_score == 0.0


def test_fusion_clamps_ai_score(engine, crypto_pass):
    """AI score > 1.0 gets clamped to 1.0."""
    result = engine.fuse({"similarity": 1.5}, crypto_pass)
    assert result.ai_score == 1.0


def test_fusion_serialization(engine, ai_pass, crypto_pass):
    """FusionResult serializes to dict."""
    result = engine.fuse(ai_pass, crypto_pass)
    d = result.to_dict()
    
    assert d["is_authentic"] is True
    assert d["decision_path"] == PATH_AUTHENTIC
    assert isinstance(d["explanations"], dict)


# ============================================================
# TAMPER DETECTION CONSISTENCY
# ============================================================

def test_any_crypto_failure_triggers_tamper(engine, ai_pass):
    """
    Any single crypto component failure should trigger tamper flag
    (because crypto_threshold is 0.95).
    """
    for failing_field in ["hmac_valid", "document_match"]:
        crypto = {"hmac_valid": True, "document_match": True, "timestamp_valid": True}
        crypto[failing_field] = False
        
        result = engine.fuse(ai_pass, crypto)
        
        # Both hmac and doc failure push score below 0.95
        if failing_field == "hmac_valid":
            assert result.crypto_score == 0.5  # fails threshold
        else:
            assert result.crypto_score == 0.6  # fails threshold
        
        assert result.tamper_detected is True
        assert result.decision_path == PATH_CRYPTO_TAMPER