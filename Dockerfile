# Use a specific Python version as the base image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  libpoppler-cpp-dev \
  libpq-dev \
  libxml2-dev \
  libxslt-dev \
  python3-dev \
  && rm -rf /var/lib/apt/lists/*

# Install pip and necessary Python libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . .

# Create a non-root user for security
RUN useradd -m appuser
USER appuser

# Expose the port the app will run on
EXPOSE 8000

# Define the command to run your app using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]