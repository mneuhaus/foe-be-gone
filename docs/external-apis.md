# External API Documentation

This document outlines all external API calls used by the Foe Be Gone system for integration with third-party services.

## Table of Contents

- [UniFi Protect API](#unifi-protect-api)
- [OpenAI API](#openai-api)
- [Xeno-Canto API](#xeno-canto-api)

---

## UniFi Protect API

The UniFi Protect integration provides camera management and RTSP stream access for wildlife detection.

### Authentication

- **Method**: API Key authentication
- **Header**: `X-API-KEY: {apiKey}`
- **Certificate Handling**: Self-signed certificates are accepted by setting `NODE_TLS_REJECT_UNAUTHORIZED='0'`

### Base URL Format

```
https://{host}/proxy/protect/integration/v1/
```

Where `{host}` is the UniFi Protect controller hostname or IP address.

### API Endpoints

#### 1. Get System Information

**Purpose**: Test connection and retrieve system metadata

```http
GET /proxy/protect/integration/v1/meta/info
Headers:
  X-API-KEY: {apiKey}
  Accept: application/json
```

**Response Example**:
```json
{
  "applicationVersion": "4.0.53"
}
```

**Used in**: Connection testing (`testUniFiProtectConnection`)

#### 2. List Cameras

**Purpose**: Retrieve all available cameras from the UniFi Protect system

```http
GET /proxy/protect/integration/v1/cameras
Headers:
  X-API-KEY: {apiKey}
  Accept: application/json
```

**Response Example**:
```json
[
  {
    "id": "64a1b2c3d4e5f6789abc123",
    "name": "Front Door Camera",
    "modelKey": "UVC-G4-PRO",
    "state": "CONNECTED",
    "isMicEnabled": true,
    "featureFlags": {
      "hasHdr": true,
      "smartDetectTypes": ["person", "vehicle"],
      "smartDetectAudioTypes": ["smoke", "co"],
      "videoModes": ["hd", "uhd"],
      "hasMic": true,
      "hasLedStatus": true,
      "hasSpeaker": false
    },
    "smartDetectSettings": {
      "objectTypes": ["person"],
      "audioTypes": []
    }
  }
]
```

**Used in**: Camera discovery (`getUniFiProtectCameras`)

### Error Handling

- **401 Unauthorized**: Invalid API key
- **404 Not Found**: Controller not found or endpoint unavailable
- **SSL Errors**: Handled by disabling certificate verification for self-signed certs

### Implementation Notes

- API calls are made with temporary TLS certificate validation disabled
- Original `NODE_TLS_REJECT_UNAUTHORIZED` setting is restored after each call
- Connection timeouts and network errors are handled gracefully

---

## OpenAI API

The OpenAI integration provides AI-powered content generation for foe descriptions and countermeasure recommendations.

### Authentication

- **Method**: Bearer token authentication
- **Header**: `Authorization: Bearer {apiKey}`
- **API Key Source**: Environment variable `OPENAI_API_KEY`

### Base URL

```
https://api.openai.com/v1/
```

### API Endpoints

#### 1. List Models

**Purpose**: Test API key validity and check available models

```http
GET /v1/models
Headers:
  Authorization: Bearer {apiKey}
  Content-Type: application/json
```

**Response Example**:
```json
{
  "data": [
    {
      "id": "gpt-4o",
      "object": "model",
      "created": 1677610602,
      "owned_by": "openai"
    },
    {
      "id": "gpt-4o-mini",
      "object": "model",
      "created": 1677610602,
      "owned_by": "openai"
    }
  ]
}
```

**Used in**: API key validation (`testOpenAIConnection`)

#### 2. Chat Completions

**Purpose**: Generate AI content for foe descriptions and countermeasures

```http
POST /v1/chat/completions
Headers:
  Authorization: Bearer {apiKey}
  Content-Type: application/json

Body:
{
  "model": "gpt-4o-mini",
  "messages": [
    {
      "role": "system",
      "content": "You are a wildlife expert specializing in animal behavior and humane deterrent methods..."
    },
    {
      "role": "user",
      "content": "Describe crows in detail for wildlife camera detection systems..."
    }
  ],
  "max_tokens": 300,
  "temperature": 0.7
}
```

**Response Example**:
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Crows are large, intelligent corvid birds measuring 17-21 inches with distinctive all-black plumage..."
      },
      "finish_reason": "stop"
    }
  ]
}
```

**Used in**: AI content generation (`generateAIContent`)

### System Prompts

#### Foe Description Generation
```
You are a wildlife expert specializing in animal behavior and humane deterrent methods. Provide accurate, practical information about animals and effective ways to deter them from gardens and properties.
```

#### User Prompts

**For Descriptions**:
```
Describe {foeName} in detail for wildlife camera detection systems. Include physical characteristics (size, color, distinctive features), behavioral patterns, typical habitats, and movement patterns that would help AI identify them in camera footage. Focus on visual and behavioral traits useful for automated detection. Keep it concise but informative (2-3 sentences).
```

**For Countermeasures**:
```
List effective, humane deterrent methods for {foeName}. Include: 1) Audio deterrents (specific sounds, frequencies, calls), 2) Visual deterrents (reflective objects, predator decoys, etc.), 3) Physical barriers, 4) Motion-activated devices. Specify what does NOT work for this species. Focus on practical, wildlife-friendly solutions. Format as a clear, actionable list.
```

### Model Selection

- **Primary Model**: `gpt-4o-mini` (cost-effective, good performance)
- **Fallback**: `gpt-4o` (higher capability, higher cost)
- **Token Limit**: 300 tokens (sufficient for concise descriptions)
- **Temperature**: 0.7 (balanced creativity and consistency)

---

## Xeno-Canto API

The Xeno-Canto integration provides access to bird sound recordings for countermeasure audio generation.

### Authentication

- **Method**: API Key (optional, for rate limiting)
- **Header**: `X-API-KEY: {apiKey}` (when available)
- **API Key Source**: Environment variable `XENOCANTO_API_KEY`

### Base URL

```
https://xeno-canto.org/api/2/
```

### API Endpoints

#### 1. Search Recordings

**Purpose**: Search for bird sound recordings by species name and other criteria

```http
GET /api/2/recordings?query={searchQuery}
Headers:
  X-API-KEY: {apiKey} (optional)
  Accept: application/json
```

**Query Parameters**:
- `query`: Search query string (species name, type, quality, etc.)
- `page`: Page number for pagination
- `format`: Response format (default: json)

**Example Query**:
```
https://xeno-canto.org/api/2/recordings?query=corvus+corax+type:call+q:A
```

**Response Example**:
```json
{
  "numRecordings": "1234",
  "numSpecies": "1",
  "page": 1,
  "numPages": 25,
  "recordings": [
    {
      "id": "123456",
      "gen": "Corvus",
      "sp": "corax",
      "ssp": "",
      "en": "Northern Raven",
      "rec": "John Smith",
      "cnt": "United States",
      "loc": "Alaska",
      "lat": "64.0685",
      "lng": "-152.2782",
      "alt": "150",
      "type": "call",
      "sex": "unknown",
      "stage": "adult",
      "method": "field recording",
      "url": "//xeno-canto.org/123456",
      "file": "//xeno-canto.org/123456/download",
      "file-name": "XC123456-Northern-Raven-Corvus-corax.mp3",
      "sono": {
        "small": "//xeno-canto.org/sounds/uploaded/...",
        "med": "//xeno-canto.org/sounds/uploaded/...",
        "large": "//xeno-canto.org/sounds/uploaded/..."
      },
      "osci": {
        "small": "//xeno-canto.org/sounds/uploaded/...",
        "med": "//xeno-canto.org/sounds/uploaded/..."
      },
      "lic": "//creativecommons.org/licenses/by-nc-sa/4.0/",
      "q": "A",
      "length": "0:42",
      "time": "06:30",
      "date": "2023-06-15",
      "uploaded": "2023-06-20",
      "also": ["Gyrfalcon"],
      "rmk": "Territorial call from adult bird",
      "bird-seen": "yes",
      "animal-seen": "no",
      "playback-used": "no",
      "temp": "12",
      "regnr": "ML123456789",
      "auto": "no",
      "dvc": "Zoom H5",
      "mic": "built-in",
      "smp": "48000"
    }
  ]
}
```

#### 2. Download Recording

**Purpose**: Download MP3 audio file for countermeasure playback

```http
GET /sounds/uploaded/{path}/{filename}
Headers:
  User-Agent: Foe-Be-Gone/1.0 (Wildlife Deterrent System)
```

**Example**:
```
https://xeno-canto.org/123456/download
```

**Response**: Binary MP3 file

### Search Query Syntax

The Xeno-Canto API uses a specific query syntax for filtering recordings:

#### Species Search
- `genus species`: Search by scientific name (e.g., `corvus corax`)
- `"common name"`: Search by common name (e.g., `"northern raven"`)

#### Quality Filters
- `q:A`: Highest quality recordings only
- `q:B`: Good quality recordings
- `q:C`: Fair quality recordings

#### Type Filters
- `type:call`: Bird calls only
- `type:song`: Bird songs only
- `type:alarm`: Alarm calls only

#### Geographic Filters
- `cnt:"country name"`: Filter by country
- `loc:"location"`: Filter by specific location

#### Example Queries Used
```
corvus corax type:call q:A          // Raven calls, high quality
corvus corone type:alarm q:A        // Crow alarm calls, high quality
pica pica type:call q:B             // Magpie calls, good quality
```

### Rate Limiting

- **Anonymous**: 100 requests per hour
- **With API Key**: 1000 requests per hour
- **Recommendation**: Include API key for production use

### Usage in Application

#### Sound Discovery Workflow
1. Search for species-specific recordings using scientific names
2. Filter by call type (call, alarm) and quality (A or B)
3. Download high-quality MP3 files for local storage
4. Organize sounds by species in `/public/sounds/{species}/` directories

#### File Naming Convention
```
XC{recording-id} - {species-name} - {scientific-name}.mp3
```

Example: `XC123456 - Northern Raven - Corvus corax.mp3`

### Error Handling

- **Rate Limiting**: Implement exponential backoff for 429 responses
- **Network Errors**: Retry with fallback to cached/local sounds
- **Audio Quality**: Prefer A-quality recordings, fallback to B-quality

### Attribution Requirements

Xeno-Canto recordings require proper attribution:
- **License**: Most recordings use Creative Commons licenses
- **Attribution**: Include recordist name and Xeno-Canto ID
- **Display**: Show attribution in UI when playing sounds

---

## API Integration Patterns

### Error Handling Strategy

All external API calls implement consistent error handling:

1. **Network Timeouts**: 30-second timeouts for all requests
2. **Retry Logic**: Exponential backoff for temporary failures
3. **Graceful Degradation**: Fallback to cached/local data when possible
4. **User Feedback**: Clear error messages in the UI

### Security Considerations

1. **API Keys**: Stored as environment variables, never in code
2. **Certificate Validation**: Disabled only for known self-signed certificates (UniFi)
3. **Rate Limiting**: Respect API rate limits to avoid service disruption
4. **Data Validation**: All API responses validated before use

### Monitoring and Logging

1. **Request Logging**: All external API calls are logged with timing
2. **Error Tracking**: Failed requests logged with error details
3. **Performance Metrics**: Response times tracked for optimization

### Environment Variables Required

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...

# Anthropic Configuration (alternative to OpenAI)
ANTHROPIC_API_KEY=sk-ant-...

# Xeno-Canto Configuration (optional)
XENOCANTO_API_KEY=your-api-key

# UniFi Protect Configuration
UNIFI_PROTECT_HOST=https://10.0.42.213
UNIFI_PROTECT_API_KEY=your-unifi-api-key
```

---

## Development and Testing

### Local Development

1. Configure API keys via the web interface (Settings > General)
2. Use test API keys where available
3. Mock external services for faster development

### Production Deployment

1. Configure all required API keys
2. Set up monitoring for API health
3. Implement caching for frequently accessed data
4. Configure backup strategies for critical API dependencies

### API Documentation Sources

- **UniFi Protect**: [Official UniFi Integration Guide](docs/UnifiProtectAPI.md)
- **OpenAI**: [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- **Xeno-Canto**: [Xeno-Canto API Documentation](https://xeno-canto.org/explore/api)