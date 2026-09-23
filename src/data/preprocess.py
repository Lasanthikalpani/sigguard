"""Image preprocessing for SigGuard (RQ1, RQ6)."""
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple


class SignaturePreprocessor:
    """Preprocess signature images for Siamese CNN.

    Pipeline:
        1. Load grayscale
        2. Denoise (Non-Local Means)
        3. Binarize (Otsu)
        4. Deskew
        5. Resize
        6. Normalize
    """

    def __init__(self, target_size: Tuple[int, int] = (224, 224)):
        self.target_size = target_size

    def load_image(self, path) -> np.ndarray:
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Could not load image: {path}")
        return img

    def denoise(self, img: np.ndarray, h: int = 10) -> np.ndarray:
        return cv2.fastNlMeansDenoising(img, h=h)

    def binarize(self, img: np.ndarray) -> np.ndarray:
        _, binary = cv2.threshold(
            img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        return binary

    def deskew(self, img: np.ndarray) -> np.ndarray:
        coords = np.column_stack(np.where(img > 0))
        if len(coords) < 10:
            return img

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) < 0.5:
            return img

        h, w = img.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        rotated = cv2.warpAffine(
            img, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated

    def resize(self, img: np.ndarray) -> np.ndarray:
        return cv2.resize(img, self.target_size, interpolation=cv2.INTER_AREA)

    def normalize(self, img: np.ndarray) -> np.ndarray:
        return img.astype(np.float32) / 255.0

    def __call__(self, path) -> np.ndarray:
        img = self.load_image(path)
        img = self.denoise(img)
        img = self.binarize(img)
        img = self.deskew(img)
        img = self.resize(img)
        img = self.normalize(img)
        return img


if __name__ == "__main__":
    test_img = np.random.randint(0, 255, (300, 300), dtype=np.uint8)
    cv2.imwrite("test_sig.png", test_img)

    preprocessor = SignaturePreprocessor(target_size=(224, 224))
    processed = preprocessor("test_sig.png")
    print(f"Processed shape: {processed.shape}")
    print(f"Value range: [{processed.min():.3f}, {processed.max():.3f}]")

    import os
    os.remove("test_sig.png")
    print("Preprocessing test passed!")