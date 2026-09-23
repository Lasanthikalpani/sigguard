"""Integration tests for SigGuard API."""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    # Use context manager to trigger lifespan (model loading)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_images():
    return {
        'genuine_1': 'tests/data/genuine_1.png',
        'genuine_2': 'tests/data/genuine_2.png',
        'forged_1': 'tests/data/forged_1.png',
    }


def test_root(client):
    response = client.get('/')
    assert response.status_code == 200
    data = response.json()
    assert data['name'] == 'SigGuard API'


def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'
    assert data['model_loaded'] is True


def test_verify_genuine_pair(client, sample_images):
    with open(sample_images['genuine_1'], 'rb') as f1, \
         open(sample_images['genuine_2'], 'rb') as f2:
        response = client.post(
            '/verify',
            files={
                'reference': ('genuine_1.png', f1, 'image/png'),
                'test': ('genuine_2.png', f2, 'image/png'),
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert 'verdict' in data
    assert 'confidence' in data
    assert 0 <= data['confidence'] <= 1


def test_verify_forged_pair(client, sample_images):
    with open(sample_images['genuine_1'], 'rb') as f1, \
         open(sample_images['forged_1'], 'rb') as f2:
        response = client.post(
            '/verify',
            files={
                'reference': ('genuine_1.png', f1, 'image/png'),
                'test': ('forged_1.png', f2, 'image/png'),
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert 'verdict' in data


def test_openapi_has_verify_endpoint(client):
    response = client.get('/openapi.json')
    assert response.status_code == 200
    openapi = response.json()
    assert '/verify' in openapi['paths']
