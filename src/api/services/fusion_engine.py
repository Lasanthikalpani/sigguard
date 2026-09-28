"""
RQ3: Fusion Engine
Combines AI (Siamese CNN) and cryptographic (QR/HMAC) verification
into a single tamper-evident authentication decision.

This is the core innovation of RQ3: weighted fusion of two independent
authentication signals to achieve >=95% tamper detection reliability.

Decision logic:
1. Crypto failure → immediate tamper flag (hard constraint)
2. AI failure → suspicious (soft constraint)
3. Both pass + weighted score high → authentic
4. Otherwise → low confidence

The engine also provides ROC-based threshold calibration to achieve
target tamper detection rates on validation data.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List, Tuple
import numpy as np


@dataclass
class FusionResult:
    """
    Combined decision from AI + cryptographic verification.
    
    Fields:
        is_authentic: Final decision (True = authentic document)
        confidence: Weighted combined score (0-1)
        ai_score: AI similarity score (0-1)
        crypto_score: Cryptographic verification score (0-1)
        tamper_detected: True if any tamper signal detected
        decision_path: Which decision branch was taken
        explanations: Detailed breakdown for human review
    """
    is_authentic: bool
    confidence: float
    ai_score: float
    crypto_score: float
    tamper_detected: bool
    decision_path: str
    explanations: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON responses."""
        return asdict(self)


# Decision path constants
PATH_AUTHENTIC = "HYBRID_AUTHENTIC"
PATH_CRYPTO_TAMPER = "CRYPTO_TAMPER"
PATH_AI_SUSPICIOUS = "AI_SUSPICIOUS"
PATH_LOW_CONFIDENCE = "LOW_CONFIDENCE"


class FusionEngine:
    """
    Weighted fusion of AI and cryptographic scores.
    
    Default configuration:
        AI weight:     0.40 (Siamese CNN similarity)
        Crypto weight: 0.60 (SHA-256 + HMAC verification)
        AI threshold:     0.85 (below → AI_SUSPICIOUS)
        Crypto threshold: 0.95 (below → CRYPTO_TAMPER)
        Fusion threshold: 0.95 (below → LOW_CONFIDENCE)
    
    The crypto weight is higher because cryptographic verification is
    deterministic (no false positives if HMAC is properly implemented),
    while AI has inherent probabilistic uncertainty.
    """
    
    def __init__(
        self,
        ai_weight: float = 0.40,
        crypto_weight: float = 0.60,
        ai_threshold: float = 0.85,
        crypto_threshold: float = 0.95,
        fusion_threshold: float = 0.95,
    ):
        # Validate weights sum to 1.0
        total = ai_weight + crypto_weight
        if not (0.99 <= total <= 1.01):
            raise ValueError(
                f"Weights must sum to 1.0 (got {total})"
            )
        
        self.ai_weight = ai_weight
        self.crypto_weight = crypto_weight
        self.ai_threshold = ai_threshold
        self.crypto_threshold = crypto_threshold
        self.fusion_threshold = fusion_threshold
    
    # ============================================================
    # CRYPTO SCORE COMPUTATION
    # ============================================================
    
    def compute_crypto_score(self, verification: Dict[str, Any]) -> float:
        """
        Convert a crypto verification result into a 0-1 score.
        
        Weighting of components:
            HMAC valid:      0.5 (detects QR tampering)
            Document match:  0.4 (detects content tampering)
            Timestamp valid: 0.1 (informational)
        
        Args:
            verification: Dict from CryptoService.verify_integrity_record()
        
        Returns:
            Score in [0.0, 1.0]
        """
        score = 0.0
        if verification.get("hmac_valid"):
            score += 0.5
        if verification.get("document_match"):
            score += 0.4
        if verification.get("timestamp_valid"):
            score += 0.1
        return round(score, 4)
    
    # ============================================================
    # MAIN FUSION LOGIC
    # ============================================================
    
    def fuse(
        self,
        ai_result: Dict[str, Any],
        crypto_result: Dict[str, Any],
    ) -> FusionResult:
        """
        Fuse AI and crypto verification results into a single decision.
        
        Args:
            ai_result: {'similarity': float, 'prediction': str, ...}
                - similarity: AI similarity score in [0, 1]
                - prediction: 'genuine' or 'forged' (optional)
            crypto_result: {'hmac_valid': bool, 'document_match': bool, ...}
                - From CryptoService.verify_integrity_record()
        
        Returns:
            FusionResult with combined decision
        """
        # Extract AI score
        ai_score = float(ai_result.get("similarity", 0.0))
        ai_score = max(0.0, min(1.0, ai_score))  # Clamp to [0, 1]
        
        # Compute crypto score
        crypto_score = self.compute_crypto_score(crypto_result)
        
        # Weighted fusion
        combined = (
            self.ai_weight * ai_score +
            self.crypto_weight * crypto_score
        )
        combined = round(combined, 4)
        
        # Decision logic with hard constraints
        crypto_failed = crypto_score < self.crypto_threshold
        ai_failed = ai_score < self.ai_threshold
        
        if crypto_failed:
            # HARD CONSTRAINT: crypto failure → tamper
            decision_path = PATH_CRYPTO_TAMPER
            is_authentic = False
            tamper_detected = True
        elif ai_failed:
            # Soft constraint: AI failure → suspicious
            decision_path = PATH_AI_SUSPICIOUS
            is_authentic = False
            tamper_detected = False
        elif combined >= self.fusion_threshold:
            # Both pass + high combined score → authentic
            decision_path = PATH_AUTHENTIC
            is_authentic = True
            tamper_detected = False
        else:
            # Both pass but combined score low (shouldn't happen with
            # proper thresholds, but defensive)
            decision_path = PATH_LOW_CONFIDENCE
            is_authentic = False
            tamper_detected = False
        
        # Build explanations
        explanations = self._build_explanations(
            ai_result=ai_result,
            crypto_result=crypto_result,
            ai_score=ai_score,
            crypto_score=crypto_score,
            combined=combined,
        )
        
        return FusionResult(
            is_authentic=is_authentic,
            confidence=combined,
            ai_score=ai_score,
            crypto_score=crypto_score,
            tamper_detected=tamper_detected,
            decision_path=decision_path,
            explanations=explanations,
        )
    
    def _build_explanations(
        self,
        ai_result: Dict[str, Any],
        crypto_result: Dict[str, Any],
        ai_score: float,
        crypto_score: float,
        combined: float,
    ) -> Dict[str, Any]:
        """Build human-readable explanation breakdown."""
        return {
            "weights": {
                "ai": self.ai_weight,
                "crypto": self.crypto_weight,
            },
            "thresholds": {
                "ai": self.ai_threshold,
                "crypto": self.crypto_threshold,
                "fusion": self.fusion_threshold,
            },
            "ai_breakdown": {
                "similarity": ai_score,
                "prediction": ai_result.get("prediction", "unknown"),
                "weighted_contribution": round(self.ai_weight * ai_score, 4),
            },
            "crypto_breakdown": {
                "score": crypto_score,
                "hmac_valid": crypto_result.get("hmac_valid", False),
                "document_match": crypto_result.get("document_match", False),
                "timestamp_valid": crypto_result.get("timestamp_valid", False),
                "weighted_contribution": round(
                    self.crypto_weight * crypto_score, 4
                ),
                "details": crypto_result.get("details", {}),
            },
            "combined_confidence": combined,
            "components_passed": {
                "crypto": crypto_score >= self.crypto_threshold,
                "ai": ai_score >= self.ai_threshold,
                "fusion": combined >= self.fusion_threshold,
            },
        }
    
    # ============================================================
    # THRESHOLD CALIBRATION (ACHIEVE >=95% TAMPER DETECTION)
    # ============================================================
    
    def calibrate_thresholds(
        self,
        validation_results: List[Dict[str, Any]],
        target_tpr: float = 0.95,
    ) -> Dict[str, float]:
        """
        Calibrate fusion threshold to achieve target TPR (True Positive Rate)
        on validation data.
        
        Args:
            validation_results: List of dicts with keys:
                - 'is_tampered': bool (ground truth)
                - 'combined_score': float (from fuse().confidence)
            target_tpr: Target tamper detection rate (default 0.95)
        
        Returns:
            Dict with optimal threshold, TPR, FPR, and stats
        """
        if not validation_results:
            return {
                "error": "No validation data provided",
                "target_tpr": target_tpr,
            }
        
        # Extract arrays
        y_true = np.array([r["is_tampered"] for r in validation_results])
        scores = np.array([r["combined_score"] for r in validation_results])
        
        # For tamper detection: "positive" = tampered
        # We want low scores → tampered
        # So we invert: tamper_score = 1 - combined_score
        tamper_scores = 1.0 - scores
        
        # Sort by tamper score (descending)
        order = np.argsort(-tamper_scores)
        y_sorted = y_true[order]
        
        # Compute cumulative TPR and FPR
        n_pos = max(int(y_true.sum()), 1)
        n_neg = max(len(y_true) - n_pos, 1)
        
        tps = np.cumsum(y_sorted)
        fps = np.cumsum(~y_sorted.astype(bool))
        
        tpr = tps / n_pos
        fpr = fps / n_neg
        
        # Find threshold achieving target TPR (smallest FPR)
        valid_idx = np.where(tpr >= target_tpr)[0]
        if len(valid_idx) == 0:
            # Cannot achieve target; use most lenient
            optimal_idx = len(tpr) - 1
        else:
            optimal_idx = valid_idx[0]
        
        optimal_tamper_score = tamper_scores[order][optimal_idx]
        optimal_threshold = 1.0 - optimal_tamper_score
        
        return {
            "optimal_threshold": float(round(optimal_threshold, 4)),
            "target_tpr": target_tpr,
            "achieved_tpr": float(round(tpr[optimal_idx], 4)),
            "achieved_fpr": float(round(fpr[optimal_idx], 4)),
            "n_samples": len(validation_results),
            "n_tampered": int(n_pos),
            "n_clean": int(n_neg),
        }
    
    # ============================================================
    # UTILITY
    # ============================================================
    
    def update_weights(
        self,
        ai_weight: Optional[float] = None,
        crypto_weight: Optional[float] = None,
    ) -> None:
        """
        Update fusion weights.
        Both must be provided, or neither (keeps current).
        """
        new_ai = ai_weight if ai_weight is not None else self.ai_weight
        new_crypto = (
            crypto_weight if crypto_weight is not None else self.crypto_weight
        )
        
        total = new_ai + new_crypto
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Weights must sum to 1.0 (got {total})")
        
        self.ai_weight = new_ai
        self.crypto_weight = new_crypto
    
    def update_thresholds(
        self,
        ai_threshold: Optional[float] = None,
        crypto_threshold: Optional[float] = None,
        fusion_threshold: Optional[float] = None,
    ) -> None:
        """Update decision thresholds."""
        if ai_threshold is not None:
            self.ai_threshold = ai_threshold
        if crypto_threshold is not None:
            self.crypto_threshold = crypto_threshold
        if fusion_threshold is not None:
            self.fusion_threshold = fusion_threshold
    
    def __repr__(self) -> str:
        return (
            f"FusionEngine("
            f"ai_weight={self.ai_weight}, "
            f"crypto_weight={self.crypto_weight}, "
            f"ai_thr={self.ai_threshold}, "
            f"crypto_thr={self.crypto_threshold}, "
            f"fusion_thr={self.fusion_threshold})"
        )