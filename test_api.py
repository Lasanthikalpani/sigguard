"""SigGuard API test script."""
import requests

API_URL = 'http://localhost:8000'


def test_health():
    print('=' * 50)
    print('Test 1: Health Check')
    print('=' * 50)
    response = requests.get(f'{API_URL}/health')
    print(f'Status: {response.status_code}')
    print(f'Response: {response.json()}')
    return response.status_code == 200


def test_genuine_pair():
    print()
    print('=' * 50)
    print('Test 2: Genuine Signature Pair')
    print('=' * 50)
    with open('tests/data/genuine_1.png', 'rb') as f1, \
         open('tests/data/genuine_2.png', 'rb') as f2:
        files = {
            'reference': ('genuine_1.png', f1, 'image/png'),
            'test': ('genuine_2.png', f2, 'image/png'),
        }
        response = requests.post(f'{API_URL}/verify', files=files)
    print(f'Status: {response.status_code}')
    result = response.json()
    print('Verdict:', result['verdict'])
    print('Confidence:', result['confidence'])
    print('Distance:', result['distance'])
    print('Inference time (ms):', result['inference_time_ms'])
    return result


def test_forged_pair():
    print()
    print('=' * 50)
    print('Test 3: Forged Signature Pair')
    print('=' * 50)
    with open('tests/data/genuine_1.png', 'rb') as f1, \
         open('tests/data/forged_1.png', 'rb') as f2:
        files = {
            'reference': ('genuine_1.png', f1, 'image/png'),
            'test': ('forged_1.png', f2, 'image/png'),
        }
        response = requests.post(f'{API_URL}/verify', files=files)
    print(f'Status: {response.status_code}')
    result = response.json()
    print('Verdict:', result['verdict'])
    print('Confidence:', result['confidence'])
    print('Distance:', result['distance'])
    print('Inference time (ms):', result['inference_time_ms'])
    return result


if __name__ == '__main__':
    print()
    print('#' * 50)
    print('# SigGuard API Test Suite')
    print('#' * 50)

    test_health()
    test_genuine_pair()
    test_forged_pair()

    print()
    print('=' * 50)
    print('All tests completed')
    print('=' * 50)
