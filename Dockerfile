FROM python:3.12-slim

WORKDIR /app

# Install uv for faster package management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY server.py .
COPY mcp_services/ ./mcp_services/

# Command to run the server
CMD ["uv", "run", "server.py"]
