# Minimal Python sandbox for secure code execution
FROM python:3.11-slim

# Create non-root user for execution
RUN useradd -m -u 1000 -s /bin/bash sandbox && \
    mkdir -p /sandbox /tmp/execution && \
    chown -R sandbox:sandbox /sandbox /tmp/execution

# Install only essential packages that students might need
# Intentionally minimal to reduce attack surface
RUN pip install --no-cache-dir numpy==1.24.3

# Set up security restrictions
RUN chmod 755 /sandbox && \
    chmod 1777 /tmp

# Set working directory
WORKDIR /sandbox

# Switch to non-root user
USER sandbox

# Set Python to run in isolated mode
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONNOUSERSITE=1 \
    PYTHONPATH=/sandbox

# Default command (will be overridden)
CMD ["python", "-c", "print('Sandbox ready')"]