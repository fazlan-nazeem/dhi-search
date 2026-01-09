FROM dhi.io/python:3.11-debian12-dev

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY input.txt .
COPY dhi_search.py .

# Run the script
CMD ["python", "dhi_search.py"]
