# CLAUDE.md - Development Guidelines

## Project: Foe Be Gone (Crow Detection & Deterrent System)

### Core Principle: Step-by-Step Development

**IMPORTANT**: We develop this project one small piece at a time. Each implementation step must be:
1. Discussed and agreed upon BEFORE coding
2. Fully functional (no placeholders or "coming soon")
3. Tested with Playwright before moving to the next step

### Development Workflow

1. **Discussion Phase**
   - User describes what feature/component to build next
   - Claude proposes implementation approach
   - Agreement reached before any code is written

2. **Implementation Phase**
   - Implement ONLY the agreed-upon feature
   - No extra features or "nice to haves"
   - No placeholder content

3. **Testing Phase**
   - **MANDATORY**: Write Playwright tests for ALL implemented features
   - Test both happy path and error scenarios
   - Include edge cases and user interactions
   - Run tests to verify functionality
   - Fix any issues before proceeding
   - **NO EXCEPTIONS**: Every feature must have tests

### Tech Stack - "Vibe-Coding" Approach

| Layer                      | Library / Tool                                             | One-liner rationale                                                   |
| -------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------- |
| **Web server**             | **FastAPI + Uvicorn `--reload`**                           | Pythonic, typed endpoints; live-reload in dev with a single flag.     |
| **HTML rendering**         | **Jinja2 templates**                                       | Classic server-side pages—no JSON plumbing required.                  |
| **Data models / ORM**      | **SQLModel**                                               | One class doubles as Pydantic schema *and* SQLAlchemy table.          |
| **Database**               | **SQLite ≥3.35**                                           | Single-file ACID DB; now supports `ALTER TABLE … DROP/RENAME COLUMN`. |
| **Migrations**             | **Alembic** (`render_as_batch=True`)                       | Autogenerates scripts; batch mode rewrites tables safely on SQLite.   |
| **Styling & components**   | **Tailwind CSS + daisyUI**                                 | Utility workflow plus 35 ready-made themes—zero JS payload.           |
| **Frontend JS (optional)** | Vanilla ES-modules (add Alpine/hyperscript only if needed) | Sprinkle just the behaviour you actually need.                        |
| **Acceptance tests**       | **Pytest + Playwright**                                    | Drive a real browser with a pure-Python API; `pytest --browser=all`.  |
| **Package management**     | **uv**                                                     | Lightning-fast Python package installer and resolver.                  |

### Dev workflow in three commands

```bash
# 1 – run the app with backend hot-reload
uvicorn app.main:app --reload --reload-include '*.html' '*.jinja'

# 2 – evolve the schema without nuking data
alembic revision --autogenerate -m "change" && alembic upgrade head

# 3 – prove it works end-to-end
pytest --browser=chromium
```

### Project Structure

```
foe-be-gone/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── models/                 # SQLModel data models (domain-separated)
│   │   ├── camera.py           # Camera-related models
│   │   ├── detection.py        # Detection and analysis models
│   │   ├── integration.py      # Integration provider models
│   │   └── setting.py          # Application settings models
│   ├── routes/                 # FastAPI route handlers (domain-separated)
│   │   ├── api/                # API endpoints
│   │   │   ├── cameras.py      # Camera management API
│   │   │   ├── detections.py   # Detection data API
│   │   │   └── integrations.py # Integration testing API
│   │   ├── dashboard.py        # Dashboard page routes
│   │   └── settings.py         # Settings page routes
│   ├── templates/              # Jinja2 HTML templates
│   ├── static/                 # CSS, JS, images
│   └── core/                   # Configuration, database, etc.
├── alembic/                    # Database migrations
├── tests/                      # Pytest + Playwright tests
├── public/                     # Static assets (sounds, images)
├── docs/                       # API documentation
└── CLAUDE.md                   # This file
```

### Code Organization Philosophy

**Domain-Separated Files (Symfony-Style)**

**AVOID monolithic Python files** that grow into unmanageable monsters. Instead of cramming everything into massive files like `models.py` or `routes.py`, we organize code by **logical domains**:

**✅ Preferred Approach:**
```
models/
├── camera.py           # Camera, CameraConfig, CameraStatus
├── detection.py        # Detection, Foe, AnalysisResult  
├── integration.py      # IntegrationProvider, Integration
└── setting.py          # Setting, AIModelConfig

routes/api/
├── cameras.py          # GET/POST/PUT/DELETE /api/cameras/*
├── detections.py       # GET/POST /api/detections/*
└── integrations.py     # POST /api/integrations/test

routes/
├── dashboard.py        # GET /dashboard, GET /dashboard/live
├── settings.py         # GET/POST /settings/*
└── home.py             # GET /, GET /status
```

**❌ Avoid This:**
```
models.py               # 500+ lines with all models mixed together
routes.py               # 1000+ lines handling every endpoint
views.py                # Giant file with all page logic
```

**Benefits of Domain Separation:**
- **Easier navigation**: Find camera logic in `models/camera.py`
- **Reduced merge conflicts**: Teams can work on different domains
- **Better imports**: `from app.models.camera import Camera`
- **Logical boundaries**: Each file has a clear, single responsibility
- **Maintainable growth**: New features get their own files

**Implementation Rules:**
1. **One domain per file**: Camera logic stays in camera-related files
2. **Clear naming**: File names should immediately indicate their contents
3. **Logical grouping**: Related models/routes/services live together
4. **Import clarity**: `from app.models.detection import Foe` is clearer than `from app.models import Foe`
5. **Size limits**: If a domain file grows beyond ~200 lines, consider splitting it further

### Cognitive Load Reduction

**Write code that minimizes mental effort** - inspired by [zakirullin's cognitive load principles](https://minds.md/zakirullin/cognitive):

**✅ Simplify Conditionals:**
```python
# Good: Self-descriptive variables
camera_is_online = camera.status == "connected"
has_permission = user.can_access_camera(camera.id)
if camera_is_online and has_permission:
    start_recording()

# Avoid: Complex nested conditions  
if camera.status == "connected" and user.permissions.get("cameras", {}).get(camera.id, False):
    start_recording()
```

**✅ Use Early Returns (Guard Clauses):**
```python
def process_detection(image_data, camera_id):
    if not image_data:
        return {"error": "no_image_data"}
    
    if not camera_exists(camera_id):
        return {"error": "camera_not_found"}
    
    # Happy path logic here - no nesting needed
    return analyze_image(image_data)
```

**✅ Self-Descriptive Error Codes:**
```python
# Good: Clear, actionable errors
return {"code": "camera_offline", "message": "Camera must be online to start recording"}

# Avoid: Generic or numeric codes
return {"error": 500, "message": "Internal server error"}
```

**Key Principle**: Before writing code, ask **"Does this increase or reduce cognitive load?"**

### Environment Setup

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project and install dependencies
uv init
uv add fastapi uvicorn[standard] sqlmodel alembic jinja2 playwright pytest

# Development dependencies
uv add --dev pytest-playwright

# Install Playwright browsers
playwright install
```

### Development Commands

```bash
# Database operations
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head                               # Apply migrations
alembic downgrade -1                               # Rollback one migration

# Development
uvicorn app.main:app --reload --reload-include '*.html' '*.jinja'  # Start dev server
uv run python -m app.main                         # Alternative start method

# Testing
pytest --browser=chromium                         # Run Playwright tests
pytest --browser=all                              # Test all browsers
pytest -v                                         # Verbose test output
```

### Rules for Claude

1. **DO NOT** implement features not explicitly requested
2. **DO NOT** add placeholder content or "coming soon" messages
3. **DO NOT** implement multiple features at once
4. **ALWAYS** wait for user approval before coding
5. **ALWAYS** write Playwright tests for implemented features - NO EXCEPTIONS
6. **ALWAYS** ensure each feature is fully working before moving on
7. **ALWAYS** use the established tech stack (FastAPI + SQLModel + Jinja2)
8. **ALWAYS** follow SQLModel patterns for database models
9. **ALWAYS** use FastAPI dependency injection for database sessions
10. **ALWAYS** include proper Python type hints
11. **ALWAYS** handle self-signed certificates for local API calls
12. **ALWAYS** use Tailwind CSS + daisyUI for styling
13. **MANDATORY**: Create comprehensive tests covering all user interactions and edge cases
14. **CRITICAL**: ALWAYS READ THE DOCUMENTATION FILES IN THE `docs/` FOLDER BEFORE IMPLEMENTING ANY EXTERNAL API INTEGRATION! The user has provided specific API documentation that MUST be followed exactly.

### Testing Guidelines

**CRITICAL LESSON LEARNED**: Tests must include realistic data scenarios!

- Write Playwright tests for all user-facing features
- Use isolated test database for each test
- Test both happy path and error scenarios
- Include proper test selectors for reliable element identification
- Test API integrations with real endpoints when possible

**⚠️ IMPORTANT - Test Data Requirements:**
- **ALWAYS seed test database with realistic data scenarios**
- **Test with both complete and incomplete data** (e.g., null references)
- **Include edge cases in test data** (detections without foe matches, etc.)
- **Test actual UI rendering with data**, not just empty states
- **Use SQLModel factories for consistent test data**

### Integration Development Pattern

When adding new integrations:
1. Define SQLModel classes for the provider
2. Create Alembic migration for schema changes
3. Implement FastAPI routes for API testing
4. Add provider-specific API calls
5. Create Jinja2 templates for UI
6. Write comprehensive Playwright tests
7. Handle authentication and certificates properly

### Current Status

**Project Reset**: Migrated from complex JavaScript stack to simple Python stack for better maintainability and development velocity.

**Ready for Implementation:**
- Base FastAPI application structure
- SQLModel database models
- Jinja2 template system
- Tailwind CSS + daisyUI styling
- Playwright testing framework

**Preserved Assets:**
- ✅ External API documentation (UniFi, OpenAI, Xeno-Canto)
- ✅ Bird sound library in `public/sounds/`
- ✅ Project logo and branding
- ✅ Understanding of integration requirements

### Development Memories

- never use alerts, use notifications

### Release Process - IMPORTANT!

**⚠️ CRITICAL: Follow these steps IN ORDER to create a proper release:**

1. **Update version in config.yaml FIRST**
   ```bash
   # Edit config.yaml and update the version field
   # Example: version: "1.0.2" -> version: "1.0.3"
   ```

2. **Commit the version update**
   ```bash
   git add config.yaml
   git commit -m "Bump version to X.Y.Z"
   git push
   ```

3. **Create and push tag**
   ```bash
   git tag vX.Y.Z -m "vX.Y.Z - Release Title"
   git push origin vX.Y.Z
   ```

4. **Create GitHub release**
   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z - Release Title" --notes "Release notes..."
   ```

**Why this order matters:**
- The Home Assistant builder reads the version from `config.yaml` at build time
- If you create the tag before updating config.yaml, it will build with the OLD version
- This has caused v1.0.1 to be built when we intended v1.0.2

**Common mistakes to avoid:**
- ❌ Creating tag before updating config.yaml
- ❌ Forgetting to push the config.yaml change before tagging
- ❌ Using different version numbers in tag vs config.yaml

Awaiting user direction for next development phase.