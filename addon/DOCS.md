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
3. Configure your OpenAI API key and preferences
4. Start the add-on

## Configuration

### Required Settings

- **openai_api_key**: Your OpenAI API key for GPT-4 Vision access
  - Get one at https://platform.openai.com/api-keys
  - Requires GPT-4 Vision access

### Optional Settings

- **detection_interval**: How often to check cameras (seconds, default: 10)
- **min_foe_confidence**: Minimum confidence to trigger deterrent (0.1-1.0, default: 0.7)
- **enable_deterrent**: Enable automatic deterrent sounds (default: true)
- **deterrent_duration**: Maximum deterrent sound duration (seconds, default: 10)
- **enable_notifications**: Send HA notifications on detections (default: true)
- **log_level**: Logging verbosity (DEBUG/INFO/WARNING/ERROR, default: INFO)

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

- GitHub Issues: [Link to repo]
- Home Assistant Community: [Link to thread]

## Privacy

- Images are processed by OpenAI's API
- Snapshots are stored locally in `/data/snapshots`
- No data is shared except with OpenAI for analysis