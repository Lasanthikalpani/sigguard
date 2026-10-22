# src/models/dual_stream_cnn.py
import torch
import torch.nn as nn

class DualStreamCNN(nn.Module):
    def __init__(self, num_classes=5):
        super(DualStreamCNN, self).__init__()
        
        # --- Stream 1: Document Content Stream ---
        self.content_stream = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128), nn.ReLU(), nn.MaxPool2d(2),
        )
        
        # --- Stream 2: QR Integrity Stream ---
        self.qr_stream = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128), nn.ReLU(), nn.MaxPool2d(2),
        )
        
        self.gap = nn.AdaptiveAvgPool2d((1, 1))
        
        # Attention Mechanism
        self.attention = nn.Sequential(
            nn.Linear(128 * 2, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )
        
        # Classifier
        self.fc = nn.Linear(128 * 2, num_classes)
        
    def forward(self, x):
        content_features = self.content_stream(x)
        qr_features = self.qr_stream(x)
        
        content_pooled = self.gap(content_features).view(content_features.size(0), -1)
        qr_pooled = self.gap(qr_features).view(qr_features.size(0), -1)
        
        combined = torch.cat((content_pooled, qr_pooled), dim=1)
        
        attention_weights = self.attention(combined)
        weighted_features = combined * attention_weights
        
        output = self.fc(weighted_features)
        return output