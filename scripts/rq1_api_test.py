"""RQ1 API Test — සම්පූර්ණ API Verification."""
import requests
import json
from pathlib import Path

API_URL = 'http://localhost:8000'
TEST_DIR = Path('data/splits_v2/test')

TEST_SIGNERS = ['signer_11', 'signer_15', 'signer_21', 'signer_45', 'signer_49']


def test_health():
    print('=' * 60)
    print('TEST 1: Health Check')
    print('=' * 60)
    response = requests.get(f'{API_URL}/health', timeout=10)
    print(f'Status: {response.status_code}')
    print(f'Response: {response.json()}')
    print()
    return response.status_code == 200


def test_pair(signer, ref_file, test_file, expected):
    print(f'=' * 60)
    print(f'{expected.upper()} PAIR — {signer}')
    print(f'=' * 60)
    print(f'Reference: {ref_file.name}')
    print(f'Test:      {test_file.name}')
    print()

    with open(ref_file, 'rb') as f1, open(test_file, 'rb') as f2:
        files = {
            'reference': (ref_file.name, f1, 'image/png'),
            'test': (test_file.name, f2, 'image/png'),
        }
        response = requests.post(f'{API_URL}/verify', files=files, timeout=30)

    result = response.json()
    print(f'Status: {response.status_code}')
    print(f'Verdict: {result.get("verdict")}')
    print(f'Confidence: {result.get("confidence"):.4f}')
    print(f'Distance: {result.get("distance"):.4f}')
    print(f'Inference time: {result.get("inference_time_ms"):.2f} ms')
    print()
    return result


if __name__ == '__main__':
    print()
    print('#' * 60)
    print('# SigGuard RQ1 API Test Suite')
    print('#' * 60)
    print()

    # Test 1: Health
    test_health()

    # Test 2: Genuine pairs
    print('=' * 60)
    print('TEST 2: GENUINE PAIRS')
    print('=' * 60)
    print()

    genuine_results = []
    for signer in TEST_SIGNERS:
        signer_dir = TEST_DIR / 'genuine' / signer
        images = sorted(signer_dir.glob('*.png'))
        if len(images) < 2:
            print(f'{signer}: Not enough images')
            continue
        result = test_pair(signer, images[0], images[1], 'genuine')
        genuine_results.append({'signer': signer, 'result': result})

    # Test 3: Forged pairs
    print('=' * 60)
    print('TEST 3: FORGED PAIRS')
    print('=' * 60)
    print()

    forged_results = []
    for signer in TEST_SIGNERS:
        genuine_dir = TEST_DIR / 'genuine' / signer
        forged_dir = TEST_DIR / 'forged' / signer

        if not forged_dir.exists():
            print(f'{signer}: No forged images')
            continue

        genuine_images = sorted(genuine_dir.glob('*.png'))
        forged_images = sorted(forged_dir.glob('*.png'))

        if not genuine_images or not forged_images:
            continue

        result = test_pair(signer, genuine_images[0], forged_images[0], 'forged')
        forged_results.append({'signer': signer, 'result': result})

    # Summary
    print()
    print('=' * 60)
    print('TEST SUMMARY')
    print('=' * 60)
    print()

    print('GENUINE PAIRS:')
    correct_genuine = 0
    for r in genuine_results:
        verdict = r['result'].get('verdict')
        status = 'PASS' if verdict == 'genuine' else 'FAIL'
        if verdict == 'genuine':
            correct_genuine += 1
        print(f'  {r["signer"]}: {verdict} (distance: {r["result"].get("distance"):.4f}) [{status}]')

    print()
    print('FORGED PAIRS:')
    correct_forged = 0
    for r in forged_results:
        verdict = r['result'].get('verdict')
        status = 'PASS' if verdict == 'forged' else 'FAIL'
        if verdict == 'forged':
            correct_forged += 1
        print(f'  {r["signer"]}: {verdict} (distance: {r["result"].get("distance"):.4f}) [{status}]')

    print()
    print('=' * 60)
    print(f'Genuine: {correct_genuine}/{len(genuine_results)} correct')
    print(f'Forged:  {correct_forged}/{len(forged_results)} correct')
    print(f'Total:   {correct_genuine + correct_forged}/{len(genuine_results) + len(forged_results)} correct')
    print('=' * 60)

    # Save
    output = {
        'genuine_results': [
            {
                'signer': r['signer'],
                'verdict': r['result'].get('verdict'),
                'distance': r['result'].get('distance'),
                'confidence': r['result'].get('confidence'),
                'inference_time_ms': r['result'].get('inference_time_ms'),
            } for r in genuine_results
        ],
        'forged_results': [
            {
                'signer': r['signer'],
                'verdict': r['result'].get('verdict'),
                'distance': r['result'].get('distance'),
                'confidence': r['result'].get('confidence'),
                'inference_time_ms': r['result'].get('inference_time_ms'),
            } for r in forged_results
        ],
        'summary': {
            'genuine_correct': correct_genuine,
            'genuine_total': len(genuine_results),
            'forged_correct': correct_forged,
            'forged_total': len(forged_results),
            'total_correct': correct_genuine + correct_forged,
            'total': len(genuine_results) + len(forged_results),
        },
    }

    output_file = Path('docs/rq1_api_test_results.json')
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print()
    print(f'Results saved: {output_file}')
    print()