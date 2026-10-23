# scripts/train_ai_model.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms
from src.models.dual_stream_cnn import DualStreamCNN
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
...

# ============================================================
# CONFIGURATION
# ============================================================
DATA_DIR = "data/ai_training_data"
EPOCHS = 30
BATCH_SIZE = 32
LR = 0.0001
TRAIN_RATIO = 0.7
VAL_RATIO = 0.15

if not os.path.exists(DATA_DIR):
    print(f"Error: {DATA_DIR} not found. Run prepare_ai_data.py first.")
    exit(1)

# ============================================================
# DATA LOADING
# ============================================================
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

dataset = datasets.ImageFolder(root=DATA_DIR, transform=transform)
print(f"Total images: {len(dataset)}")
print(f"Classes: {dataset.classes}")

train_size = int(TRAIN_RATIO * len(dataset))
val_size = int(VAL_RATIO * len(dataset))
test_size = len(dataset) - train_size - val_size
print(f"Train: {train_size} | Val: {val_size} | Test: {test_size}")

train_dataset, val_dataset, test_dataset = random_split(
    dataset, [train_size, val_size, test_size],
    generator=torch.Generator().manual_seed(42)
)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

# ============================================================
# MODEL SETUP
# ============================================================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Training on: {device}")

model = DualStreamCNN(num_classes=len(dataset.classes)).to(device)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=LR)
scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

# ============================================================
# TRAINING LOOP
# ============================================================
start_time = time.time()
best_val_acc = 0.0
history = []

for epoch in range(EPOCHS):
    model.train()
    train_loss = 0.0
    for inputs, labels in train_loader:
        inputs, labels = inputs.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        train_loss += loss.item()
    
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
    avg_loss = train_loss / len(train_loader)
    
    if val_acc > best_val_acc:
        best_val_acc = val_acc
        torch.save(model.state_dict(), "best_ai_model.pth")
    
    history.append({
        "epoch": epoch + 1,
        "train_loss": round(avg_loss, 4),
        "val_accuracy": round(val_acc, 2)
    })
    
    print(f"Epoch {epoch+1}/{EPOCHS} | Loss: {avg_loss:.4f} | Val Acc: {val_acc:.2f}%")
    scheduler.step()

train_time = time.time() - start_time

# ============================================================
# TEST EVALUATION
# ============================================================
model.load_state_dict(torch.load("best_ai_model.pth"))
model.eval()

all_preds = []
all_labels = []
start_inference = time.time()

with torch.no_grad():
    for inputs, labels in test_loader:
        inputs, labels = inputs.to(device), labels.to(device)
        outputs = model(inputs)
        _, predicted = torch.max(outputs.data, 1)
        all_preds.extend(predicted.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

inference_time = (time.time() - start_inference) * 1000 / len(test_dataset)

accuracy = accuracy_score(all_labels, all_preds)
cm = confusion_matrix(all_labels, all_preds)

print(f"\n=== AI Model Results ===")
print(f"Training Time: {train_time:.2f}s")
print(f"Test Accuracy: {accuracy * 100:.2f}%")
print(f"Avg Inference Time: {inference_time:.2f} ms/image")
print("\nClassification Report:")
print(classification_report(all_labels, all_preds, target_names=dataset.classes, zero_division=0))

results = {
    "model": "Dual-Stream CNN",
    "training_time_seconds": round(train_time, 2),
    "test_accuracy_percent": round(accuracy * 100, 2),
    "inference_time_ms": round(inference_time, 2),
    "epochs": EPOCHS,
    "dataset_size": len(dataset),
    "train_size": train_size,
    "val_size": val_size,
    "test_size": test_size,
    "best_val_accuracy": round(best_val_acc, 2),
    "confusion_matrix": cm.tolist(),
    "history": history
}
with open("ai_model_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to ai_model_results.json")