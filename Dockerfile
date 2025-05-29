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

# Create application directory structure following Linux FHS
RUN mkdir -p \
    /opt/foe-be-gone/app \
    /opt/foe-be-gone/alembic \
    /opt/foe-be-gone/public \
    /opt/foe-be-gone/scripts \
    /var/lib/foe-be-gone/dev-workspace \
    /var/lib/foe-be-gone/data \
    /var/log/foe-be-gone \
    /etc/foe-be-gone \
    /usr/local/bin \
    /var/run/sshd \
    /root/.config \
    /root/.claude

# Set working directory to application root
WORKDIR /opt/foe-be-gone

# Copy dependency files
COPY pyproject.toml ./
COPY uv.lock* ./

# Install Python dependencies
RUN uv pip install --system --break-system-packages \
    --index-url https://pypi.org/simple \
    -r pyproject.toml

# Copy application code to proper locations
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY public ./public

# Create compatibility symlinks for existing code
RUN ln -s /opt/foe-be-gone /app && \
    ln -s /var/lib/foe-be-gone/dev-workspace /dev-workspace && \
    ln -s /var/lib/foe-be-gone/data /data

# Copy addon run scripts to proper locations
# Main run script for Home Assistant S6 overlay
COPY scripts/run.sh /usr/local/bin/foe-be-gone-start
# Development scripts in /opt/foe-be-gone/scripts
COPY scripts/run-test.sh /opt/foe-be-gone/scripts/
COPY scripts/dev-init.sh /opt/foe-be-gone/scripts/
COPY scripts/dev-mode.sh /opt/foe-be-gone/scripts/

# Make scripts executable
RUN chmod a+x /usr/local/bin/foe-be-gone-start \
    /opt/foe-be-gone/scripts/run-test.sh \
    /opt/foe-be-gone/scripts/dev-init.sh \
    /opt/foe-be-gone/scripts/dev-mode.sh

# Create convenience symlinks in /usr/local/bin for dev scripts
RUN ln -s /opt/foe-be-gone/scripts/dev-init.sh /usr/local/bin/foe-dev-init && \
    ln -s /opt/foe-be-gone/scripts/dev-mode.sh /usr/local/bin/foe-dev-mode

# For Home Assistant compatibility, create symlink at old location
RUN ln -s /usr/local/bin/foe-be-gone-start /run.sh

# Create empty claude settings file if it doesn't exist (for volume mounting)
RUN touch /root/.claude.json

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
    io.hass.version="1.0.20" \
    io.hass.type="addon" \
    io.hass.arch="amd64|aarch64"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["/run.sh"]