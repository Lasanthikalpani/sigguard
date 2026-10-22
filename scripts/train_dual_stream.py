import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms
from src.models.dual_stream_cnn import DualStreamCNN
from sklearn.metrics import classification_report, accuracy_score
from tqdm import tqdm

# 1. Data Augmentation (වඩාත් ආක්‍රමණශීලී)
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomRotation(15),
    transforms.RandomAffine(degrees=0, translate=(0.15, 0.15)),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# 2. Dataset Load
data_dir = 'data/rq3_layer6_eval'
dataset = datasets.ImageFolder(root=data_dir, transform=transform)

print(f"Total images: {len(dataset)}")
print(f"Classes: {dataset.classes}")
print(f"Class distribution: {dataset.targets.count(0)}, {dataset.targets.count(1)}, {dataset.targets.count(2)}, {dataset.targets.count(3)}")

# 3. Train/Val/Test Split
train_size = int(0.7 * len(dataset))
val_size = int(0.15 * len(dataset))
test_size = len(dataset) - train_size - val_size

train_dataset, val_dataset, test_dataset = random_split(
    dataset, [train_size, val_size, test_size],
    generator=torch.Generator().manual_seed(42)
)

train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True)   # Batch size අඩු කළා
val_loader = DataLoader(val_dataset, batch_size=8, shuffle=False)
test_loader = DataLoader(test_dataset, batch_size=8, shuffle=False)

# 4. Model, Loss, Optimizer
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = DualStreamCNN(num_classes=len(dataset.classes)).to(device)
criterion = nn.CrossEntropyLoss()

# Learning Rate අඩු කළා, Weight Decay එකතු කළා
optimizer = optim.Adam(model.parameters(), lr=0.0001, weight_decay=1e-4)

# Learning Rate Scheduler
scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=20, gamma=0.5)

# 5. Training Loop (Epochs 100)
epochs = 100
best_val_acc = 0.0

print(f"\nTraining on {device}...")

for epoch in range(epochs):
    # Training
    model.train()
    running_loss = 0.0
    for inputs, labels in tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}", leave=False):
        inputs, labels = inputs.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()

    # Validation
    model.eval()
    val_correct = 0
    val_total = 0
    with torch.no_grad():
        for inputs, labels in val_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            _, predicted = torch.max(outputs.data, 1)
            val_total += labels.size(0)
            val_correct += (predicted == labels).sum().item()

    val_acc = 100 * val_correct / val_total

    # හොඳම ආකෘතිය Save කරන්න
    if val_acc > best_val_acc:
        best_val_acc = val_acc
        torch.save(model.state_dict(), 'best_dual_stream_model.pth')

    if (epoch + 1) % 10 == 0:
        print(f"Epoch {epoch+1}/{epochs} | Loss: {running_loss/len(train_loader):.4f} | Val Acc: {val_acc:.2f}%")

    scheduler.step()

# 6. Test Set Evaluation
model.load_state_dict(torch.load('best_dual_stream_model.pth'))
model.eval()

all_preds = []
all_labels = []

with torch.no_grad():
    for inputs, labels in test_loader:
        inputs, labels = inputs.to(device), labels.to(device)
        outputs = model(inputs)
        _, predicted = torch.max(outputs.data, 1)
        all_preds.extend(predicted.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

# 7. Metrics
print("\n=== Dual-Stream CNN Final Evaluation ===")
print(f"Best Validation Accuracy: {best_val_acc:.2f}%")
print(f"Test Accuracy: {accuracy_score(all_labels, all_preds) * 100:.2f}%")
print("\nClassification Report:")
print(classification_report(all_labels, all_preds, target_names=dataset.classes, zero_division=0))