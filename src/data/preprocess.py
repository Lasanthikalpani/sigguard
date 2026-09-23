"""Fast image preprocessing for SigGuard (RQ1)."""
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple


class SignaturePreprocessor:
    """Fast preprocess signature images for Siamese CNN."""

    def __init__(self, target_size: Tuple[int, int] = (224, 224)):
        self.target_size = target_size

    def load_image(self, path) -> np.ndarray:
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Could not load image: {path}")
        return img

    def binarize(self, img: np.ndarray) -> np.ndarray:
        _, binary = cv2.threshold(
            img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        return binary

    def resize(self, img: np.ndarray) -> np.ndarray:
        return cv2.resize(img, self.target_size, interpolation=cv2.INTER_AREA)

    def normalize(self, img: np.ndarray) -> np.ndarray:
        return img.astype(np.float32) / 255.0

    def __call__(self, path) -> np.ndarray:
        img = self.load_image(path)
        img = self.binarize(img)
        img = self.resize(img)
        img = self.normalize(img)
        return img