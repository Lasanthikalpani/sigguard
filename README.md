# 🛡️ SigGuard

[![SigGuard CI](https://github.com/Lasanthikalpani/sigguard/actions/workflows/test.yml/badge.svg)](https://github.com/Lasanthikalpani/sigguard/actions/workflows/test.yml)

### AI-Powered Signature Forgery Detection for Sri Lankan Government Documents

**MSc Research Project** | University of Sri Jayewardenepura

---

## 🎯 Overview

**SigGuard** is an explainable AI system for detecting signature forgery in Sri Lankan government documents using **Siamese Convolutional Neural Networks** with few-shot learning, **Grad-CAM explainability**, and **hybrid cryptographic verification**.

## 🏗️ Architecture

Frontend (React) -> Backend (FastAPI) -> AI Layer (PyTorch)
                       |
              Integration (Event-driven)
                       |
              Data Layer (PostgreSQL)
                       |
              MLOps (Docker + CI/CD)

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- Git

### Installation

    # 1. Clone
    git clone https://github.com/Lasanthikalpani/sigguard.git
    cd sigguard

    # 2. Environment
    conda create -n sigguard python=3.10 -y
    conda activate sigguard
    pip install -r requirements.txt
    pip install -e .

    # 3. Docker services
    cd docker
    docker compose up -d
    cd ..

    # 4. Test
    pytest tests/ -v

    # 5. Run API
    uvicorn src.api.main:app --reload

### Services

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

## 🔬 Research Questions

| RQ | Focus | Status |
|----|-------|--------|
| RQ1 | Core AI performance (Siamese CNN + few-shot) | In Progress |
| RQ2 | Explainability & trust (Grad-CAM + LangChain) | Planned |
| RQ3 | Hybrid integration (QR + SHA-256) | Planned |
| RQ4 | Cross-script performance | Planned |
| RQ5 | Forgery type classification | Planned |
| RQ6 | Document degradation robustness | Planned |
| RQ7 | Edge deployment optimization | Planned |

## 🛠️ Tech Stack

- AI/ML: PyTorch, Siamese CNNs, Grad-CAM
- LLM: LangChain, OpenAI, FAISS, RAG
- Backend: FastAPI, Celery, Redis
- Database: PostgreSQL, SQLAlchemy
- MLOps: Docker, GitHub Actions
- Testing: pytest, pytest-cov

## 📊 Current Status

- [x] Siamese CNN model (ResNet-18 backbone)
- [x] FastAPI service (7 routes)
- [x] 5-fold CV evaluation harness
- [x] PostgreSQL integration
- [x] 10 pytest tests passing
- [x] GitHub Actions CI/CD
- [ ] RQ2-RQ7 (in progress)

## 📁 Project Structure

    sigguard/
    |-- src/
    |   |-- api/              # FastAPI service
    |   |-- models/           # PyTorch models
    |   |-- data/             # Dataset + preprocessing
    |   |-- training/         # Training loop
    |   |-- evaluation/       # Metrics
    |   |-- db/               # PostgreSQL
    |-- eval/                 # Evaluation harness
    |-- tests/                # Unit + integration
    |-- docker/               # Docker config
    |-- .github/workflows/    # CI/CD
    |-- models/checkpoints/   # Trained models
    |-- scripts/              # Utilities

## 🧪 Testing

    pytest tests/ -v

## 👤 Author

**Lasanthi Kalpani**
- MSc Computer Science, University of Sri Jayewardenepura
- GitHub: [@Lasanthikalpani](https://github.com/Lasanthikalpani)

## 📄 License

MIT
