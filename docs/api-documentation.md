# Foe Be Gone API Documentation

## Overview

Foe Be Gone provides a RESTful API for managing wildlife detection and deterrent systems. The API is built with FastAPI and includes automatic interactive documentation.

## Interactive Documentation

- **Swagger UI**: Available at `/docs` - Interactive API explorer
- **ReDoc**: Available at `/redoc` - Alternative documentation format

## Base URL

```
http://localhost:8000
```

## API Endpoints

### Health Check

#### GET /health
Check system health and version.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0"
}
```

### Detections

#### GET /detections/api/interval
Get the current detection check interval.

**Response:**
```json
{
  "interval": 10
}
```

#### POST /detections/api/interval
Set the detection check interval (1-30 seconds).

**Request Body:**
```json
{
  "interval": 15
}
```

**Response:**
```json
{
  "interval": 15,
  "message": "Detection interval updated to 15 seconds"
}
```

#### GET /detections/api/sounds
List all available deterrent sounds organized by foe type.

**Response:**
```json
{
  "crows": {
    "count": 25,
    "files": ["XC121378 - Western Jackdaw - Coloeus monedula.mp3", ...]
  },
  "rats": {
    "count": 0,
    "files": []
  },
  "cats": {
    "count": 0,
    "files": []
  }
}
```

#### POST /detections/api/sounds/test
Test playing a deterrent sound locally.

**Request Body:**
```json
{
  "foe_type": "crows"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Played deterrent sound for crows locally"
}
```

#### POST /detections/api/sounds/test-camera/{device_id}
Test playing a deterrent sound on a specific camera.

**Path Parameters:**
- `device_id`: Camera device ID

**Request Body:**
```json
{
  "foe_type": "crows"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Played deterrent sound 'XC121378 - Western Jackdaw - Coloeus monedula.mp3' on camera Front Door"
}
```

### Integrations

#### GET /api/integrations
List all configured integrations.

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "integration_type": "unifi_protect",
    "name": "UniFi Protect",
    "enabled": true,
    "status": "connected",
    "status_message": "Connected to 192.168.1.1"
  }
]
```

#### POST /api/integrations
Create a new integration instance.

**Request Body:**
```json
{
  "integration_type": "unifi_protect",
  "name": "My UniFi System",
  "config": {
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "verify_ssl": false
  }
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "integration_type": "unifi_protect",
  "name": "My UniFi System",
  "enabled": true,
  "status": "connected",
  "status_message": "Connected successfully"
}
```

#### POST /api/integrations/{integration_id}/test
Test an integration connection.

**Path Parameters:**
- `integration_id`: Integration instance ID

**Response:**
```json
{
  "success": true,
  "message": "Connection successful",
  "details": {
    "cameras_found": 3,
    "version": "2.11.21"
  }
}
```

## Error Responses

All endpoints use standard HTTP status codes and return errors in this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common status codes:
- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

## Authentication

Currently, the API does not require authentication. This may change in future versions.

## Rate Limiting

No rate limiting is currently implemented.

## WebSocket Support

The application supports WebSocket connections for real-time updates (not yet implemented).

## Examples

### Using cURL

Get detection interval:
```bash
curl http://localhost:8000/detections/api/interval
```

Set detection interval:
```bash
curl -X POST http://localhost:8000/detections/api/interval \
  -H "Content-Type: application/json" \
  -d '{"interval": 20}'
```

Test sound playback:
```bash
curl -X POST http://localhost:8000/detections/api/sounds/test \
  -H "Content-Type: application/json" \
  -d '{"foe_type": "crows"}'
```

### Using Python

```python
import requests

# Get available sounds
response = requests.get("http://localhost:8000/detections/api/sounds")
sounds = response.json()
print(f"Available crow sounds: {sounds['crows']['count']}")

# Test sound playback
response = requests.post(
    "http://localhost:8000/detections/api/sounds/test",
    json={"foe_type": "crows"}
)
print(response.json())
```

## Video Capture Feature

When a foe is detected, the system now automatically:
1. Captures a 15-second video clip from the camera's RTSP stream
2. Saves the video to `data/videos/` directory
3. Links the video to the detection record

### Requirements
- FFmpeg must be installed on the system
- Camera must provide an RTSP stream URL
- Sufficient disk space for video storage

### Video File Naming
Videos are saved with the format:
```
{camera_name}_{timestamp}_det{detection_id}_{random_id}.mp4
```

Example: `Front_Door_20250527_143022_det42_a1b2c3d4.mp4`