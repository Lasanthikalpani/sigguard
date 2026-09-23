"""Unit tests for Siamese model (TDD)."""
import pytest
import torch
from src.models.siamese import SiameseNetwork, ContrastiveLoss, TripletLoss


@pytest.fixture
def model():
    return SiameseNetwork(embedding_dim=128, backbone='resnet18', pretrained=False)


def test_model_output_shape(model):
    x1 = torch.randn(4, 3, 224, 224)
    x2 = torch.randn(4, 3, 224, 224)
    emb1, emb2 = model(x1, x2)
    assert emb1.shape == (4, 128)
    assert emb2.shape == (4, 128)


def test_contrastive_loss(model):
    x1 = torch.randn(4, 3, 224, 224)
    x2 = torch.randn(4, 3, 224, 224)
    emb1, emb2 = model(x1, x2)
    labels = torch.tensor([0, 1, 0, 1], dtype=torch.float32)
    criterion = ContrastiveLoss(margin=1.0)
    loss = criterion(emb1, emb2, labels)
    assert loss.item() >= 0


def test_triplet_loss():
    anchor = torch.randn(4, 128)
    positive = torch.randn(4, 128)
    negative = torch.randn(4, 128)
    criterion = TripletLoss(margin=1.0)
    loss = criterion(anchor, positive, negative)
    assert loss.item() >= 0


def test_model_deterministic():
    model = SiameseNetwork(embedding_dim=128, backbone='resnet18', pretrained=False)
    model.eval()
    x = torch.randn(1, 3, 224, 224)
    with torch.no_grad():
        emb1 = model.forward_once(x)
        emb2 = model.forward_once(x)
    torch.testing.assert_close(emb1, emb2)


def test_parameter_count(model):
    total = sum(p.numel() for p in model.parameters())
    assert total > 1_000_000
    assert total < 50_000_000
