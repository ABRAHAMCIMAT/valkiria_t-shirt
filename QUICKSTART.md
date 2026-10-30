# Quick Start Guide - Epic Estimation System

## Prerequisites
- Python 3.12 installed
- Node.js 18+ installed  
- The provided JIRA CSV file (Jira (3).csv) in the root directory

## Step 1: Setup Backend

Open PowerShell and run:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Step 2: Setup Frontend

Open another PowerShell window and run:

```powershell
cd frontend
npm install
```

## Step 3: Train Models (one-time)

In the backend PowerShell window:

```powershell
# Run the backend server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open a third PowerShell window:

```powershell
cd backend
# Train models using the provided CSV
python -c "
from models.epic_estimation_models import create_and_train_models
models = create_and_train_models('../Jira (3).csv', 'trained_models')
"
```

Or use curl (after backend starts):

```powershell
curl.exe -F "file=@..\Jira (3).csv" http://localhost:8000/train
```

## Step 4: Run Frontend

In the frontend PowerShell window:

```powershell
npm run dev
```

## Step 5: Access the Application

Open browser: `http://localhost:3000`

## What You Can Do

1. Upload the provided `HU_260226.xlsx` file for estimation
2. See predictions for Story Points, Time, Cost, and Effort
3. Compare Random Forest vs Decision Tree models
4. Export results to CSV

## Useful URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- API Health Check: http://localhost:8000/health

## Stopping Services

- Backend: Press Ctrl+C in backend PowerShell
- Frontend: Press Ctrl+C in frontend PowerShell

## Troubleshooting

If port 8000 is in use, change it:
```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
Then update frontend environment variable or API URL.

If npm install fails, try:
```powershell
npm install --legacy-peer-deps
```
