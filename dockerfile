# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create directory for the app
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip==23.0.1 && pip install --no-cache-dir -r requirements.txt

# Copy project files into the container
COPY . /app/

# Expose port 5000 (Flask default)
EXPOSE 5000

# Run the Flask application
CMD ["python", "app.py"]