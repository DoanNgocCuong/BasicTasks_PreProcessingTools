FROM python:3.9

# Set working directory
WORKDIR /app

# Copy files
COPY . .

# Set permissions for sensitive files
RUN chmod 600 /app/config.py

# Install dependencies
RUN pip install -r requirements.txt

# Set environment variables for Flask
ENV FLASK_APP=apiPacking.py
ENV FLASK_ENV=development
ENV PORT=3000

# Expose port
EXPOSE 3000

# Command to run your application
CMD ["flask", "run", "--host=0.0.0.0", "--port=3000"]


# Successfully built 6d55b095cdb7
# Successfully tagged larkbase-api:latest
# SECURITY WARNING: You are building a Docker image from Windows against a non-Windows Docker host. All files and directories added to build context will have '-rwxr-xr-x' permissions. It is recommended to double check and reset permissions for sensitive files and directories.

