# Use a Python 3.9 base image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port the Flask app will run on
EXPOSE 5000

# Command to run the Flask application with Gunicorn
# Gunicorn is used for production deployment to handle requests efficiently
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]