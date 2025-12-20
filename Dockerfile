FROM python:3.13-slim

LABEL org.opencontainers.image.source=https://github.com/zorkian/chibichonk
LABEL org.opencontainers.image.description="Bambu Labs 3D Printer Discord Monitor"
LABEL org.opencontainers.image.licenses=MIT

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY chibichonk.py .

# Config will be mounted from host
VOLUME ["/app/config"]

# Run the application
CMD ["python", "-u", "chibichonk.py"]
