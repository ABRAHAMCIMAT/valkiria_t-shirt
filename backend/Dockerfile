FROM python:3.12-slim

WORKDIR /app

# All dependencies ship prebuilt wheels for Python 3.12, so no compiler is needed.

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run as an unprivileged user that owns /app (models and exports are written there)
RUN useradd --create-home --uid 1000 appuser && chown -R appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
