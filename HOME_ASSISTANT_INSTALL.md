# Home Assistant Installation Guide

## Quick Install

### Step 1: Add Repository

1. Open Home Assistant
2. Go to **Supervisor** → **Add-on Store**
3. Click the **⋮** menu (top right) → **Repositories**
4. Add this URL: `https://github.com/mneuhaus/foe-be-gone`
5. Click **Add**

### Step 2: Install Add-on

1. Find "Foe Be Gone" in the add-on store
2. Click **Install** (this may take a few minutes)
3. Wait for installation to complete

### Step 3: Configure

1. Go to the **Configuration** tab
2. Add your OpenAI API key:

```yaml
openai_api_key: "sk-your-api-key-here"
detection_interval: 10
min_foe_confidence: 0.7
enable_deterrent: true
deterrent_duration: 10
enable_notifications: true
log_level: INFO
```

### Step 4: Start

1. Go to the **Info** tab
2. Enable **Start on boot** and **Auto update**
3. Click **Start**
4. Wait for startup (check logs if needed)
5. Click **Open Web UI**

## Detailed Configuration

### OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Make sure you have GPT-4 Vision access
4. Copy the key to your configuration

### Camera Integration

#### UniFi Protect Setup

1. In the Foe Be Gone web interface, go to **Settings** → **Integrations**
2. Click **Add Integration** → **UniFi Protect**
3. Configure:
   - **Host**: Your UniFi console IP (e.g., `192.168.1.100`)
   - **Username**: Local UniFi user (not Ubiquiti account)
   - **Password**: Local user password
   - **Port**: Usually `443`
   - **Verify SSL**: Turn OFF for local connections

4. Click **Test Connection**
5. If successful, click **Save**

#### Camera Requirements

- Camera must support motion detection
- Two-way audio required for deterrent sounds
- RTSP stream access needed for video capture

### Sound Configuration

Sounds are automatically included, but you can customize them:

1. Access your Home Assistant files
2. Navigate to `/addon_configs/foe_be_gone/sounds/`
3. Add custom sounds in appropriate folders:
   - `crows/` - Sounds for crows, ravens, magpies
   - `cats/` - Sounds for domestic cats
   - `rats/` - Sounds for rodents
   - `custom/` - Your own sounds

### Automation Integration

Create automations to respond to detections:

```yaml
# Example: Send notification
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
```

## Troubleshooting

### Add-on Won't Start

1. Check the **Log** tab for errors
2. Verify OpenAI API key is correct
3. Ensure sufficient system resources
4. Check network connectivity

### No Detections

1. Verify camera integration is working:
   - Go to **Settings** → **Integrations**
   - Check connection status
   - Test camera access

2. Check motion detection:
   - Ensure cameras have motion detection enabled
   - Verify motion sensitivity settings
   - Check if UniFi smart detections are working

3. Verify AI settings:
   - Check OpenAI API key is valid
   - Ensure sufficient API credits
   - Check detection confidence threshold

### Sounds Not Playing

1. Verify camera audio:
   - Check if camera supports two-way audio
   - Test speaker functionality in UniFi Protect
   - Ensure audio is enabled

2. Check sound files:
   - Verify sounds exist in `/addon_configs/foe_be_gone/sounds/`
   - Test sound file formats (MP3, WAV supported)
   - Check file permissions

### High Costs

Monitor and reduce OpenAI API costs:

1. **Increase detection interval**: Set to 30+ seconds for less frequent checks
2. **Adjust confidence threshold**: Increase to 0.8+ to reduce false positives
3. **Use scheduling**: Only run during peak problem hours
4. **Optimize camera zones**: Focus motion detection on problem areas only

### Performance Issues

1. **Check system resources**:
   - Ensure adequate CPU/RAM
   - Monitor disk space for snapshots/videos
   - Check network bandwidth for video processing

2. **Optimize settings**:
   - Reduce video capture duration
   - Lower camera resolution if possible
   - Increase detection intervals during low-activity periods

## Support

- 📚 [Full Documentation](https://github.com/mneuhaus/foe-be-gone)
- 🐛 [Report Issues](https://github.com/mneuhaus/foe-be-gone/issues)
- 💬 [Community Discussions](https://github.com/mneuhaus/foe-be-gone/discussions)
- 📧 Email: support@foe-be-gone.com

## Updates

The add-on will automatically update when you have **Auto update** enabled. You can also manually update from the add-on store.

Check the [CHANGELOG](addon/CHANGELOG.md) for new features and fixes.