# Use a Python 3.11 base image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements file first to take advantage of Docker caching
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all other backend files (including plant_disease_prediction_model.h5 and diseases.json)
COPY . .

# Expose port (Hugging Face Spaces uses 7860 by default)
EXPOSE 7860

# Set environment variable for port
ENV PORT=7860

# Start Flask server
CMD ["python", "server.py"]
