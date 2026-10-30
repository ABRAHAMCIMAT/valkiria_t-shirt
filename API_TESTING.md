# Epic Estimation System - API Testing Guide

This guide shows how to test the Epic Estimation API using curl or Python.

## Prerequisites

- Backend running on `http://localhost:8000`
- Python 3.12 or curl installed

## 1. Health Check

Verify the API is running:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "models_loaded": false,
  "timestamp": "2026-08-16T10:00:00"
}
```

## 2. Training Models

Before predictions, train the models using the JIRA CSV:

```bash
# Using curl
curl -F "file=@Jira (3).csv" http://localhost:8000/train

# Using Python
import requests

with open('Jira (3).csv', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/train', files=files)
    print(response.json())
```

Expected response:
```json
{
  "status": "success",
  "message": "Models trained on 500 samples",
  "models": ["point", "time", "cost", "effort"],
  "model_file": "backend/trained_models/models.pkl"
}
```

## 3. Estimate Single Story

Estimate a single story:

```bash
curl -X POST http://localhost:8000/estimate/single \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Login Feature",
    "description": "Implement user login with email and password",
    "acceptance_criteria": [
      "User can enter email and password",
      "Password is encrypted",
      "Login token is returned"
    ],
    "priority": "High",
    "issue_type": "Story"
  }'
```

Using Python:

```python
import requests
import json

story = {
    "title": "Login Feature",
    "description": "Implement user login with email and password",
    "acceptance_criteria": [
        "User can enter email and password",
        "Password is encrypted",
        "Login token is returned"
    ],
    "priority": "High",
    "issue_type": "Story"
}

response = requests.post(
    'http://localhost:8000/estimate/single',
    json=story
)

print(json.dumps(response.json(), indent=2))
```

Expected response:
```json
{
  "story_title": "Login Feature",
  "point_estimate": {
    "ensemble": 5.2,
    "random_forest": 5.4,
    "decision_tree": 5.0
  },
  "time_estimate": {
    "ensemble": 3.8,
    "random_forest": 4.0,
    "decision_tree": 3.6
  },
  "cost_estimate": {
    "ensemble": 1520,
    "random_forest": 1600,
    "decision_tree": 1440
  },
  "effort_estimate": {
    "ensemble": 291.5,
    "random_forest": 296.3,
    "decision_tree": 286.7
  },
  "semantic_estimate": null
}
```

## 4. Estimate from Excel

Upload an Excel file for batch estimation:

```bash
curl -F "file=@HU_260226.xlsx" http://localhost:8000/estimate/excel
```

Using Python:

```python
import requests

with open('HU_260226.xlsx', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/estimate/excel', files=files)
    data = response.json()
    
    print(f"Total stories: {data['total']}")
    print(f"Successful: {data['successful']}")
    print(f"Failed: {data['failed']}")
    
    for result in data['results']:
        print(f"\n{result['story_title']}")
        print(f"  Points: {result['point_estimate']['ensemble']:.1f}")
        print(f"  Time: {result['time_estimate']['ensemble']:.1f} days")
        print(f"  Cost: ${result['cost_estimate']['ensemble']:.0f}")
```

## 5. Get Model Statistics

Get information about trained models:

```bash
curl http://localhost:8000/models/stats
```

Expected response:
```json
{
  "models_trained": true,
  "targets": ["point", "time", "cost", "effort"],
  "training_samples": 500,
  "features_count": 25,
  "model_location": "backend/trained_models/models.pkl"
}
```

## 6. Batch Estimation

Estimate multiple stories at once:

```bash
curl -X POST http://localhost:8000/estimate/batch \
  -H "Content-Type: application/json" \
  -d '{
    "stories": [
      {
        "title": "Story 1",
        "description": "Description 1",
        "acceptance_criteria": ["Criteria 1"]
      },
      {
        "title": "Story 2",
        "description": "Description 2",
        "acceptance_criteria": ["Criteria 2"]
      }
    ]
  }'
```

Using Python:

```python
import requests

stories = [
    {
        "title": "Story 1",
        "description": "Description 1",
        "acceptance_criteria": ["Criteria 1"]
    },
    {
        "title": "Story 2",
        "description": "Description 2",
        "acceptance_criteria": ["Criteria 2"]
    }
]

response = requests.post(
    'http://localhost:8000/estimate/batch',
    json={"stories": stories}
)

data = response.json()
print(f"Successful: {data['successful']}/{data['total']}")
```

## API Errors

Common error responses:

### 503 - Models Not Trained
```json
{
  "detail": "Models not trained. Call POST /train first."
}
```

Solution: Train models using the `/train` endpoint

### 400 - Bad Request
```json
{
  "detail": "File must be CSV format"
}
```

Solution: Ensure correct file format

### 500 - Internal Server Error
```json
{
  "detail": "Estimation failed: <error message>"
}
```

Solution: Check backend logs and ensure data is valid

## Performance Tips

1. **Batch vs Single**: Batch estimation is more efficient for multiple stories
2. **CSV Format**: Ensure proper encoding (UTF-8) for JIRA CSV
3. **Excel Format**: Use .xlsx format, avoid merged cells
4. **Model Training**: Takes time on first run, subsequent loads are fast

## Testing with Postman

If using Postman:

1. Create new request
2. Set method to POST
3. Set URL: `http://localhost:8000/estimate/single`
4. Go to "Body" tab
5. Select "raw" and "JSON"
6. Paste JSON payload
7. Send

## Automated Testing

Create a test script (`test_api.py`):

```python
#!/usr/bin/env python3
import requests
import time

BASE_URL = "http://localhost:8000"

def test_health():
    print("Testing health check...")
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    print("✓ Health check passed")

def test_train():
    print("Training models...")
    with open('Jira (3).csv', 'rb') as f:
        resp = requests.post(f"{BASE_URL}/train", files={'file': f})
    assert resp.status_code == 200
    print(f"✓ Training completed: {resp.json()['message']}")
    time.sleep(2)  # Wait for models to be saved

def test_estimate():
    print("Testing estimation...")
    story = {
        "title": "Test Story",
        "description": "Test description",
        "acceptance_criteria": ["Test criteria"]
    }
    resp = requests.post(f"{BASE_URL}/estimate/single", json=story)
    assert resp.status_code == 200
    data = resp.json()
    print(f"✓ Estimated {data['story_title']}")
    print(f"  Points: {data['point_estimate']['ensemble']:.1f}")

if __name__ == "__main__":
    test_health()
    test_train()
    test_estimate()
    print("\n✓ All tests passed!")
```

Run with:
```bash
python test_api.py
```
