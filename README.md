# Foe Be Gone 🦅

AI-powered wildlife detection and deterrent system that uses your security cameras to detect unwanted animals and automatically plays deterrent sounds to scare them away.

![GitHub Release](https://img.shields.io/github/v/release/mneuhaus/foe-be-gone)
![Docker Pulls](https://img.shields.io/docker/pulls/mneuhaus/foe-be-gone)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--on-blue)

## Features

- 🎯 **AI-Powered Detection**: Uses OpenAI GPT-4 Vision to identify animals in camera snapshots
- 🔊 **Smart Deterrents**: Plays species-specific sounds to scare away unwanted animals
- 📊 **Effectiveness Tracking**: Monitors which sounds work best for each animal type
- 📈 **Comprehensive Analytics**: Beautiful statistics dashboard with insights
- 🏠 **Home Assistant Integration**: Seamless integration with your HA instance
- 🎥 **Video Capture**: Records video clips when animals are detected
- 🐿️ **Friend Tracking**: Monitors impact on friendly creatures
- 💰 **Cost Monitoring**: Tracks AI processing costs

## Supported Animals

### Foes (Deterred)
- **Crows & Ravens**: Corvids that damage crops and property
- **Cats**: Domestic cats that hunt birds and leave waste
- **Rodents**: Rats, mice, and other pest rodents

### Friends (Protected)  
- **Small Birds**: Songbirds, finches, etc.
- **Squirrels**: Harmless garden visitors
- **Hedgehogs**: Beneficial pest controllers
- **Butterflies**: Pollinators

## Installation

### Home Assistant Add-on (Recommended)

1. **Add Repository**:
   - Go to **Supervisor** → **Add-on Store** → **⋮** → **Repositories**
   - Add: `https://github.com/mneuhaus/foe-be-gone`
   - Click **Add**

2. **Install Add-on**:
   - Find "Foe Be Gone" in the add-on store
   - Click **Install**

3. **Configure**:
   ```yaml
   openai_api_key: "sk-your-api-key-here"
   detection_interval: 10
   min_foe_confidence: 0.7
   enable_deterrent: true
   deterrent_duration: 10
   enable_notifications: true
   log_level: INFO
   ```

4. **Start the Add-on**:
   - Enable **Start on boot** and **Auto update**
   - Click **Start**
   - Click **Open Web UI**

### Docker Standalone

```bash
# Clone the repository
git clone https://github.com/mneuhaus/foe-be-gone.git
cd foe-be-gone

# Copy environment file
cp .env.example .env

# Edit .env with your settings
nano .env

# Start with Docker Compose
docker-compose up -d
```

### Manual Installation

```bash
# Clone repository
git clone https://github.com/mneuhaus/foe-be-gone.git
cd foe-be-gone

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Start the application
uv run uvicorn app.main:app --reload
```

## Configuration

### Required Settings

- **OpenAI API Key**: Get one at [OpenAI Platform](https://platform.openai.com/api-keys)
  - Requires GPT-4 Vision access
  - Typical cost: $0.01-0.03 per detection

### Camera Setup

#### UniFi Protect

1. Go to **Settings** → **Integrations**
2. Add **UniFi Protect** integration
3. Configure:
   - **Host**: Your UniFi console IP/hostname
   - **Username**: Local user (not Ubiquiti account)
   - **Password**: Local user password
   - **Verify SSL**: Usually disabled for local connections

#### Generic Cameras (Coming Soon)

Support for generic RTSP/HTTP cameras is planned.

### Sound Configuration

Sounds are stored in `/media/sounds/` (HA) or `public/sounds/` (standalone):

```
sounds/
├── crows/          # Predator calls, distress signals
├── cats/           # Dog barks, deterrent sounds  
├── rats/           # Owl calls, hawk screeches
└── custom/         # Your custom sounds
```

## Usage

### Dashboard

Access the web interface to:
- View live camera feeds
- Monitor recent detections
- Configure detection settings
- Test integrations

### Statistics

Comprehensive analytics showing:
- **Daily Trends**: Detection patterns over time
- **Sound Effectiveness**: Which sounds work best
- **Camera Performance**: Activity by device
- **Cost Analysis**: AI processing expenses
- **Friend Impact**: Effect on beneficial wildlife

### Automation

Create Home Assistant automations:

```yaml
# Send notification on detection
automation:
  - alias: "Crow Detection Alert"
    trigger:
      platform: webhook
      webhook_id: foe_be_gone_detection
    condition:
      condition: template
      value_template: "{{ trigger.json.foe_type == 'crows' }}"
    action:
      service: notify.mobile_app
      data:
        message: "Crow detected in {{ trigger.json.camera_name }}"
```

## API Documentation

Interactive API docs available at `/docs` when running.

### Key Endpoints

- `GET /api/detections` - Recent detections
- `POST /api/integrations/test` - Test camera connection
- `GET /api/statistics/live-data` - Real-time stats
- `GET /health` - Health check

## Development

### Tech Stack

- **Backend**: FastAPI + SQLModel + SQLite
- **Frontend**: Jinja2 + Tailwind CSS + daisyUI + Chart.js
- **AI**: OpenAI GPT-4 Vision
- **Video**: FFmpeg for RTSP capture
- **Testing**: Pytest + Playwright

### Development Setup

```bash
# Install development dependencies
uv sync --dev

# Install Playwright browsers
uv run playwright install

# Run tests
uv run pytest

# Start development server
uv run uvicorn app.main:app --reload
```

### Architecture

```
foe-be-gone/
├── app/
│   ├── models/          # SQLModel data models
│   ├── routes/          # FastAPI route handlers  
│   ├── services/        # Business logic
│   ├── templates/       # Jinja2 HTML templates
│   └── static/          # CSS, JS assets
├── addon/               # Home Assistant add-on config
├── tests/               # Pytest + Playwright tests
└── public/              # Static assets (sounds, images)
```

## Troubleshooting

### Common Issues

**No Detections**:
- Check camera connectivity in Settings → Integrations
- Verify OpenAI API key is valid
- Ensure motion detection is enabled on cameras

**Sounds Not Playing**:
- Verify camera supports two-way audio
- Check sound files exist in media folder
- Test audio output on camera

**High Costs**:
- Increase detection interval
- Adjust camera motion sensitivity
- Use scheduling to limit active hours

### Logs

View logs in:
- **Home Assistant**: Supervisor → Add-on → Foe Be Gone → Logs
- **Docker**: `docker-compose logs -f foe-be-gone`
- **Manual**: Application logs to stdout

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Privacy & Security

- Images are processed by OpenAI's API for analysis
- Snapshots stored locally in `/data/snapshots`
- No data shared except with OpenAI for animal identification
- Self-signed certificates supported for local camera connections

## License

MIT License - see [LICENSE](LICENSE) file.

## Support

- 🐛 [Report Issues](https://github.com/mneuhaus/foe-be-gone/issues)
- 💬 [Discussions](https://github.com/mneuhaus/foe-be-gone/discussions)
- 📧 [Email Support](mailto:support@foe-be-gone.com)

## Acknowledgments

- Bird sounds from [Xeno-canto](https://xeno-canto.org/)
- Animal detection powered by [OpenAI](https://openai.com/)
- Home Assistant integration framework

---

**Made with ❤️ for wildlife management**