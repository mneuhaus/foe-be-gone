# syntax=docker/dockerfile:1
# Home Assistant Add-on Dockerfile - Debian based
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-debian:bookworm
FROM $BUILD_FROM

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    ffmpeg \
    curl \
    git \
    openssh-server \
    bash \
    zsh \
    nodejs \
    npm \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Install pnpm and claude-code
RUN npm install -g pnpm @anthropic-ai/claude-code
ENV PNPM_HOME="/root/.local/share/pnpm"
ENV PATH="$PNPM_HOME:${PATH}"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./
COPY uv.lock* ./

# Install Python dependencies
RUN uv pip install --system --break-system-packages \
    --index-url https://pypi.org/simple \
    -r pyproject.toml

# Copy application code
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY public ./public

# Copy addon run scripts
COPY run.sh /
COPY run-test.sh /
COPY dev-init.sh /
COPY dev-mode.sh /

# Make run scripts executable
RUN chmod a+x /run.sh /run-test.sh /dev-init.sh /dev-mode.sh

# Create necessary directories
RUN mkdir -p /data /config /media/sounds /app/logs /var/run/sshd /dev-workspace

# Configure SSH for development
RUN ssh-keygen -A && \
    echo "PermitRootLogin yes" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "PermitEmptyPasswords yes" >> /etc/ssh/sshd_config && \
    passwd -d root

# Install oh-my-zsh
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended && \
    sed -i 's/ZSH_THEME="robbyrussell"/ZSH_THEME="agnoster"/' ~/.zshrc && \
    echo 'export PATH="/root/.local/bin:$PATH"' >> ~/.zshrc && \
    echo 'alias ll="ls -la"' >> ~/.zshrc && \
    echo 'alias dev="/dev-mode.sh"' >> ~/.zshrc

# Set labels
LABEL \
    io.hass.name="Foe Be Gone" \
    io.hass.description="AI-powered wildlife detection and deterrent system" \
    io.hass.version="1.0.15" \
    io.hass.type="addon" \
    io.hass.arch="amd64|aarch64"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["/run.sh"]