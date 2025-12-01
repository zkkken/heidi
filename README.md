# Heidi EMR Automation

Heidi EMR Automation is a macOS-focused RPA toolkit that extracts patient data from a desktop EMR and injects it into Heidi Health via Chrome. It mixes AI-based UI detection with hardcoded anchor coordinates for speed and reliability, and uses AppleScript-driven JavaScript injection to stay compatible with React-based forms.

## Key Features
- **Dual-targeting clicks**: Uses AI vision plus fallback hard coordinates to locate patient names and navigation tabs; deviation thresholds ensure the cursor snaps back to trusted anchors when AI results drift.【F:core/rpa_automation.py†L16-L53】
- **Robust mouse control**: Automates window detection, cursor placement, and click flows tailored for EMR-to-Heidi transfers.【F:core/rpa_automation.py†L56-L192】
- **Direct Chrome injection**: Drives Chrome through AppleScript and JavaScript rather than conventional typing/clicking, making it resilient to React-controlled inputs.【F:core/rpa_automation.py†L13-L18】【F:core/web_bridge.py†L1-L160】
- **Configurable capture + OCR**: Captures EMR screens, runs OCR with adjustable language/angle/GPU settings, and routes extracted text to Heidi APIs.【F:core/config.py†L33-L125】【F:core/ocr_parser.py†L1-L160】
- **API-ready**: Centralized Heidi API configuration and validation for authenticated uploads, timeouts, and retry rules.【F:core/config.py†L9-L91】【F:core/config.py†L127-L192】

## Requirements
- macOS with Accessibility/AppleScript permissions
- Python 3.10+
- Google Chrome
- API keys for Anthropic Claude (for vision) and Heidi Health

## Setup
1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```
   Fill in keys such as `ANTHROPIC_API_KEY`, `HEIDI_API_KEY`, and optional overrides like `HEIDI_BASE_URL` or `HEIDI_WEB_URL`. OCR and logging defaults can also be tuned via environment variables.【F:core/config.py†L33-L192】

3. **Collect anchor coordinates**
   Run the helper to record reliable click positions, then update the constants in `core/rpa_automation.py`:
   ```bash
   python tools/get_mouse_pos.py
   ```
   Coordinates such as `HARD_COORDS_FIRST_PATIENT` and `HARD_COORDS_CONSULTATIONS` act as golden anchors when AI detection is uncertain.【F:core/rpa_automation.py†L16-L53】

4. **(Optional) Adjust screenshot regions**
   If the default capture window does not match your EMR layout, set `SCREENSHOT_LEFT`, `SCREENSHOT_TOP`, `SCREENSHOT_WIDTH`, and `SCREENSHOT_HEIGHT` in `.env` or edit `DEFAULT_SCREENSHOT_REGION` in `core/config.py`.【F:core/config.py†L57-L88】

## Usage
Launch the interactive menu and choose a workflow:
```bash
python main.py
```
- **Batch schedule → Web**: Read EMR schedules, build JSON payloads, and inject them into Heidi web.
- **Precise consultations (recommended)**: AI + hard coordinate navigation to the patient, extract consultations, and inject into Heidi.
- **Single context injection**: Pull the current patient context and send it to Heidi.
- **Smart click (auto-correct)**: Use AI-guided clicks with Heidi API upload.
- **More options**: Bulk registration, fast imports, legacy menu, and deep extraction variants.【F:main.py†L15-L84】

## Project Structure
```
core/
├── rpa_automation.py   # Workflow orchestration, anchor handling, mouse control
├── ai_locator.py       # AI-driven UI element detection
├── capture.py          # Screenshot utilities and region helpers
├── ocr_parser.py       # OCR pipeline configuration and parsing
├── smart_capture.py    # Combined capture + extraction helpers
├── web_bridge.py       # AppleScript/JS bridge for Chrome injection
├── heidi_client.py     # Heidi API client helpers
└── config.py           # Environment-driven configuration and validation
main.py                 # Interactive menu entrypoint
heidi_menu.py           # Legacy menu entrypoint
```

## Troubleshooting
- **Clicks land in the wrong place**: Re-record anchor coordinates and tighten `DEVIATION_THRESHOLD` or `SAFE_THRESHOLD` in `core/rpa_automation.py`.【F:core/rpa_automation.py†L16-L53】
- **No API access**: Confirm `HEIDI_API_KEY` and base URL values in `.env`; run `validate_config()` in `core/config.py` to surface missing settings.【F:core/config.py†L127-L192】
- **Incorrect captures/OCR**: Adjust the screenshot region and OCR language/angle/GPU flags via environment variables to better match your EMR layout.【F:core/config.py†L57-L125】

## Safety Notes
- The automation is intended for controlled demonstrations; avoid using real patient data.
- Do not hardcode API keys in source files—use environment variables instead.
- Ensure macOS Accessibility permissions are granted for your terminal/IDE before running.
