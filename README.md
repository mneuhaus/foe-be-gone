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

#### Quick Install

1. **Add Repository**:
   - Go to **Supervisor** → **Add-on Store** → **⋮** → **Repositories**
   - Add: `https://github.com/mneuhaus/foe-be-gone`
   - Click **Add**

2. **Install Add-on**:
   - Find "Foe Be Gone" in the add-on store
   - Click **Install** (this may take a few minutes)

3. **Configure**:
   - Go to the **Configuration** tab
   - Add your OpenAI API key:
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
   - Go to the **Info** tab
   - Enable **Start on boot** and **Auto update**
   - Click **Start**
   - Wait for startup (check logs if needed)
   - Click **Open Web UI**

#### Detailed Setup

**OpenAI API Key Setup**:
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Make sure you have GPT-4 Vision access
4. Copy the key to your configuration

**UniFi Protect Camera Setup**:
1. In the Foe Be Gone web interface, go to **Settings** → **Integrations**
2. Click **Add Integration** → **UniFi Protect**
3. Configure:
   - **Host**: Your UniFi console IP (e.g., `192.168.1.100`)
   - **Username**: Local UniFi user (not Ubiquiti account)
   - **Password**: Local user password
   - **Port**: Usually `443`
   - **Verify SSL**: Turn OFF for local connections
4. Click **Test Connection** and **Save**

**Camera Requirements**:
- Camera must support motion detection
- Two-way audio required for deterrent sounds
- RTSP stream access needed for video capture

**Sound Customization**:
Sounds are automatically included, but you can customize:
1. Access your Home Assistant files
2. Navigate to `/addon_configs/foe_be_gone/sounds/`
3. Add custom sounds in appropriate folders (`crows/`, `cats/`, `rats/`, `custom/`)

### Docker Standalone

```bash
# Clone the repository
git clone https://github.com/mneuhaus/foe-be-gone.git
cd foe-be-gone

# Start with Docker Compose
docker-compose up -d

# Configure via web interface
# Open http://localhost:8000 and go to Settings > General
# Add your OpenAI API key and adjust other settings as needed
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

### Home Assistant Automation

Create automations to respond to detections:

```yaml
# Example: Send notification with image
automation:
  - alias: "Foe Detection Alert"
    trigger:
      platform: webhook
      webhook_id: foe_be_gone_detection
    action:
      service: notify.mobile_app_your_phone
      data:
        title: "Animal Detected!"
        message: "{{ trigger.json.foe_type }} detected on {{ trigger.json.camera_name }}"
        data:
          image: "{{ trigger.json.snapshot_url }}"
          
# Example: Turn on lights when crow detected
  - alias: "Scare Crows with Lights"
    trigger:
      platform: webhook
      webhook_id: foe_be_gone_detection
    condition:
      condition: template
      value_template: "{{ trigger.json.foe_type == 'crows' }}"
    action:
      service: light.turn_on
      target:
        entity_id: light.garden_lights
      data:
        brightness: 255
        color_name: red
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

**Add-on Won't Start**:
- Check the **Log** tab for errors in Home Assistant
- Verify OpenAI API key is correct
- Ensure sufficient system resources
- Check network connectivity

**No Detections**:
1. Verify camera integration is working:
   - Go to **Settings** → **Integrations**
   - Check connection status and test camera access
2. Check motion detection:
   - Ensure cameras have motion detection enabled
   - Verify motion sensitivity settings
   - Check if UniFi smart detections are working
3. Verify AI settings:
   - Check OpenAI API key is valid
   - Ensure sufficient API credits
   - Check detection confidence threshold

**Sounds Not Playing**:
1. Verify camera audio:
   - Check if camera supports two-way audio
   - Test speaker functionality in UniFi Protect
   - Ensure audio is enabled
2. Check sound files:
   - Verify sounds exist in `/addon_configs/foe_be_gone/sounds/`
   - Test sound file formats (MP3, WAV supported)
   - Check file permissions

**High Costs**:
Monitor and reduce OpenAI API costs:
- **Increase detection interval**: Set to 30+ seconds for less frequent checks
- **Adjust confidence threshold**: Increase to 0.8+ to reduce false positives
- **Use scheduling**: Only run during peak problem hours
- **Optimize camera zones**: Focus motion detection on problem areas only

**Performance Issues**:
1. Check system resources:
   - Ensure adequate CPU/RAM
   - Monitor disk space for snapshots/videos
   - Check network bandwidth for video processing
2. Optimize settings:
   - Reduce video capture duration
   - Lower camera resolution if possible
   - Increase detection intervals during low-activity periods

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