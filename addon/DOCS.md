# Foe Be Gone - Home Assistant Add-on

AI-powered wildlife detection and deterrent system that integrates with your security cameras to detect and deter unwanted animals.

## Features

- 🎯 **AI-Powered Detection**: Uses OpenAI GPT-4 Vision to identify animals in camera snapshots
- 🔊 **Smart Deterrents**: Plays species-specific sounds to scare away unwanted animals
- 📊 **Effectiveness Tracking**: Monitors which sounds work best for each animal type
- 📈 **Comprehensive Analytics**: Beautiful statistics dashboard with insights
- 🏠 **Home Assistant Integration**: Seamless integration with your HA instance
- 🎥 **Video Capture**: Records video clips when animals are detected
- 🐿️ **Friend Tracking**: Monitors impact on friendly creatures

## Installation

1. Add this repository to your Home Assistant add-on store
2. Install the "Foe Be Gone" add-on
3. Start the add-on
4. Open the web interface and configure your settings

## Configuration

All settings are managed through the web interface at Settings → General:

### AI & Detection Settings

- **OpenAI API Key**: Your OpenAI API key for GPT-4 Vision access
  - Get one at https://platform.openai.com/api-keys
  - Requires GPT-4 Vision access
- **Confidence Threshold**: Minimum confidence to trigger actions (0.0-1.0, default: 0.8)
- **Detection Interval**: How often to check cameras (seconds, default: 10)

### System Settings

- **Log Level**: Logging verbosity (DEBUG/INFO/WARNING/ERROR, default: INFO)
- **Max Image Size**: Maximum image size for processing (MB, default: 10)
- **Snapshot Retention**: How long to keep snapshots (days, default: 7)

## Camera Setup

### UniFi Protect

1. Go to Settings → Integrations in the add-on
2. Add UniFi Protect integration
3. Enter your UniFi console details:
   - Host: Your UniFi console IP/hostname
   - Username: Local user (not Ubiquiti account)
   - Password: Local user password
   - Verify SSL: Usually disabled for local connections

### Generic Cameras

Support for generic RTSP/HTTP cameras coming soon!

## Sound Library

The add-on includes a curated library of deterrent sounds:

- **Crows**: Predator calls, distress signals
- **Cats**: Dog barks, ultrasonic deterrents
- **Rodents**: Owl calls, hawk screeches

Sounds are stored in `/media/sounds/` and can be customized.

## Statistics

Access comprehensive analytics at the Statistics page:

- Detection trends over time
- Success rates by animal and sound
- Camera performance metrics
- Cost analysis for AI processing
- Friend vs foe ratios
- Peak activity hours

## Troubleshooting

### No Detections

1. Check camera connectivity in Settings → Integrations
2. Verify OpenAI API key is valid
3. Check logs for errors

### Sounds Not Playing

1. Ensure audio is enabled in add-on configuration
2. Check camera supports two-way audio
3. Verify sound files exist in media folder

### High Costs

1. Increase detection interval
2. Adjust camera motion zones
3. Use scheduling to limit active hours

## API Access

The add-on exposes a REST API at `/api/docs` for advanced integrations.

## Support

- GitHub Issues: https://github.com/mneuhaus/foe-be-gone/issues
- Documentation: https://github.com/mneuhaus/foe-be-gone

## Privacy

- Images are processed by OpenAI's API
- Snapshots are stored locally in `/data/snapshots`
- No data is shared except with OpenAI for analysis