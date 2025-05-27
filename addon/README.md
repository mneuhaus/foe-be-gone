# Foe Be Gone - Home Assistant Add-on

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]
![Supports armv7 Architecture][armv7-shield]

AI-powered wildlife detection and deterrent system for Home Assistant.

## About

Foe Be Gone uses your existing security cameras to detect unwanted animals (like crows, cats, and rodents) and automatically plays deterrent sounds through the camera's speaker to scare them away. It tracks effectiveness over time to learn which sounds work best.

## Features

- 🎯 AI-powered animal detection using GPT-4 Vision
- 🔊 Automatic deterrent sounds through camera speakers
- 📊 Effectiveness tracking and analytics
- 📈 Beautiful statistics dashboard
- 🎥 Video capture during detection events
- 🐿️ Friend vs foe tracking
- 🏠 Seamless Home Assistant integration

## Installation

1. Add this repository to your Home Assistant add-on store:
   ```
   https://github.com/mneuhaus/foe-be-gone
   ```

2. Click "Install" on the Foe Be Gone add-on

3. Configure your OpenAI API key in the add-on configuration

4. Start the add-on

5. Click "Open Web UI" to access the interface

## Configuration

```yaml
openai_api_key: "sk-..."  # Required: Your OpenAI API key
detection_interval: 10     # How often to check cameras (seconds)
min_foe_confidence: 0.7    # Minimum confidence to trigger deterrent
enable_deterrent: true     # Enable automatic deterrent sounds
deterrent_duration: 10     # Maximum sound duration (seconds)
enable_notifications: true # Send HA notifications
log_level: INFO           # Logging verbosity
```

## Supported Cameras

- UniFi Protect (full support with two-way audio)
- Generic RTSP cameras (coming soon)
- Frigate integration (planned)

## Screenshot

![Dashboard](https://raw.githubusercontent.com/mneuhaus/foe-be-gone/main/screenshots/dashboard.png)

## Support

Please open an issue on GitHub for support.

## License

MIT License

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg