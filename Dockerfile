# Image with Python 3.11 and uv (fast package manager) pre-installed
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Install gh CLI
RUN apt-get update -y && \
    apt-get install -y curl && \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt-get update -y && apt-get install -y gh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

# Install project dependencies using uv (reads pyproject.toml)
RUN uv pip install --system .

ENTRYPOINT ["python", "main.py"]
