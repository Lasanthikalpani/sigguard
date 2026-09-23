"""Siamese Neural Network for signature verification (RQ1).

SigGuard - AI-Powered Signature Forgery Detection
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models
from typing import Tuple


class SiameseNetwork(nn.Module):
    """Siamese network with ResNet backbone for signature verification.

    Args:
        embedding_dim: Dimension of output embedding (default: 128).
        backbone: Backbone architecture ('resnet18', 'resnet50', 'mobilenet').
        pretrained: Whether to use pretrained weights.
    """

    def __init__(
        self,
        embedding_dim: int = 128,
        backbone: str = "resnet18",
        pretrained: bool = True,
    ):
        super().__init__()
        self.embedding_dim = embedding_dim
        self.backbone_name = backbone

        if backbone == "resnet18":
            weights = models.ResNet18_Weights.DEFAULT if pretrained else None
            resnet = models.resnet18(weights=weights)
            feature_dim = 512
            self.backbone = nn.Sequential(*list(resnet.children())[:-1])
        elif backbone == "resnet50":
            weights = models.ResNet50_Weights.DEFAULT if pretrained else None
            resnet = models.resnet50(weights=weights)
            feature_dim = 2048
            self.backbone = nn.Sequential(*list(resnet.children())[:-1])
        elif backbone == "mobilenet":
            weights = models.MobileNet_V2_Weights.DEFAULT if pretrained else None
            mobilenet = models.mobilenet_v2(weights=weights)
            feature_dim = 1280
            self.backbone = nn.Sequential(*list(mobilenet.children())[:-1])
        else:
            raise ValueError(f"Unknown backbone: {backbone}")

        self.embedding = nn.Sequential(
            nn.Linear(feature_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, embedding_dim),
        )

    def forward_once(self, x: torch.Tensor) -> torch.Tensor:
        features = self.backbone(x)
        features = features.view(features.size(0), -1)
        return self.embedding(features)

    def forward(
        self, x1: torch.Tensor, x2: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.forward_once(x1), self.forward_once(x2)


class ContrastiveLoss(nn.Module):
    """Contrastive loss for Siamese networks."""

    def __init__(self, margin: float = 1.0):
        super().__init__()
        self.margin = margin

    def forward(self, emb1, emb2, label):
        distance = F.pairwise_distance(emb1, emb2, keepdim=True)
        positive_loss = (1 - label) * 0.5 * distance ** 2
        negative_loss = label * 0.5 * F.relu(self.margin - distance) ** 2
        return torch.mean(positive_loss + negative_loss)


class TripletLoss(nn.Module):
    """Triplet loss with margin."""

    def __init__(self, margin: float = 1.0):
        super().__init__()
        self.margin = margin

    def forward(self, anchor, positive, negative):
        pos_dist = F.pairwise_distance(anchor, positive, keepdim=True)
        neg_dist = F.pairwise_distance(anchor, negative, keepdim=True)
        loss = F.relu(pos_dist - neg_dist + self.margin)
        return torch.mean(loss)


if __name__ == "__main__":
    model = SiameseNetwork(embedding_dim=128, backbone="resnet18")
    x1 = torch.randn(4, 3, 224, 224)
    x2 = torch.randn(4, 3, 224, 224)
    emb1, emb2 = model(x1, x2)
    print("SigGuard Siamese Network")
    print(f"  Embedding shape: {emb1.shape}")
    print(f"  Parameters: {sum(p.numel() for p in model.parameters()):,}")