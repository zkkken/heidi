# Heidi Health API Integration Guide

**Version**: 2.0 (Verified against Official Documentation)
**Base URL**: `https://registrar.api.heidihealth.com/api/v2/ml-scribe/open-api`

---

## 1. Authentication (Critical)

Heidi API uses a **Key-to-JWT** exchange mechanism. Note that `POST /jwt` is deprecated/incorrect; you must use `GET /jwt`.

### Step 1: Exchange API Key for JWT

- **Endpoint**: `GET /jwt`
- **Headers**:
  - `Heidi-Api-Key`: `<YOUR_SHARED_API_KEY>` (Case-sensitive)
  - `Content-Type`: `application/json`
- **Query Parameters**:
  - `email`: Unique identifier for the user (e.g., `doctor@clinic.com`)
  - `third_party_internal_id`: Your system's user ID (e.g., `user_123`)

**Example Request:**

```http
GET https://registrar.api.heidihealth.com/api/v2/ml-scribe/open-api/jwt?email=doc@test.com&third_party_internal_id=123
Header: Heidi-Api-Key: sk-12345...
```

**Response:**

```json
{
  "token": "eyJhbGciOiJIUzI1Ni..." // Use this Bearer token for all subsequent requests
}
```

### Step 2: Account Linking (Required for 400 Error)

**Error**: `Linked Account is required. Please link your account before using this feature.`

**Solution**:
The API user (shadow account) created in Step 1 must be linked to a real Heidi Health account once.

1. Generate a JWT using Step 1.
2. Construct a Widget URL: `https://scribe.heidihealth.com/widget?token=<JWT_TOKEN>`
3. Open this URL in a browser.
4. Log in with valid Heidi credentials.
5. **Result**: The API Key + Email combination is now authorized to create patients/notes via API.

---

## 2. API Endpoints (Bearer Auth)

All subsequent requests must use the JWT from Step 1.

- **Header**: `Authorization: Bearer <JWT_TOKEN>`

### Create Patient Profile

- **URL**: `POST /patient-profiles` (Append to Base URL)
- **Payload**:
  ```json
  {
    "first_name": "John",
    "last_name": "Doe",
    "birth_date": "1980-01-01", // Format: YYYY-MM-DD
    "gender": "male",           // Options: male, female, other
    "ehr_patient_id": "MRN123"
  }
  ```

### Create Patient (Alternative, Lighter)

- **URL**: `POST /patients`
- **Payload**:
  ```json
  {
    "first_name": "John",
    "last_name": "Doe",
    "birth_date": "1980-01-01",
    "gender": "male",
    "external_id": "MRN123"
  }
  ```

**Note**: `/patients` endpoint is lighter and doesn't require linked account for basic patient creation. Use this if you encounter "Linked Account required" errors.

### Create Session (Consultation)

- **URL**: `POST /sessions`
- **Payload**:
  ```json
  {
    "patient_profile_id": "<ID_FROM_ABOVE>",
    "start_time": "2023-10-27T10:00:00Z"
  }
  ```

---

## 3. Common Errors & Fixes

| Error Code | Message Fragment | Cause | Fix |
|:-----------|:-----------------|:------|:----|
| **404** | `Not Found` | Incorrect Base URL | Ensure Base URL ends with `/open-api`. Do not append extra `/api/v1`. |
| **400** | `Linked Account is required` | Unlinked Shadow Account | Perform **Step 2 (Account Linking)** manually once per email, OR use `/patients` endpoint instead of `/patient-profiles`. |
| **401/403** | `Unauthorized` | Invalid/Expired Token | JWT tokens expire. Refresh token using `GET /jwt` every hour. |
| **500+** | `NameResolutionError` | DNS Issue | Verify `registrar.api.heidihealth.com` is accessible. |

---

## 4. Implementation Notes

### Current Implementation in `core/heidi_client.py`

1. **Authentication**: Uses `GET /jwt` with `Heidi-Api-Key` header
2. **Patient Creation**:
   - Primary: `/patients` endpoint (lighter, no linked account needed)
   - Fallback: `/patient-profiles` endpoint (requires linked account)
3. **Token Caching**: JWT tokens are cached and reused until expiry
4. **Demo Mode**: Falls back to `MOCK_TOKEN_FOR_DEMO` if authentication fails

### Recommended Workflow

```python
from core.heidi_client import HeidiClient

# Initialize client
client = HeidiClient()

# Authenticate (automatically called when needed)
client.authenticate()

# Create patient (using lighter endpoint)
patient_data = {
    "first_name": "John",
    "last_name": "Doe",
    "birth_date": "1980-01-01",
    "gender": "male",
    "phone": "0412345678"
}

result = client.create_patient(patient_data)
```

---

## 5. Troubleshooting

### Issue: "Linked Account is required"

**Solution**:
1. **Option A**: Perform one-time account linking:
   - Get JWT token
   - Visit `https://scribe.heidihealth.com/widget?token=<YOUR_JWT>`
   - Log in with Heidi account

2. **Option B**: Use `/patients` endpoint instead of `/patient-profiles`

### Issue: Token expires frequently

**Solution**:
- Tokens typically last 1 hour
- The client automatically refreshes on 401 errors
- For long-running processes, consider implementing a refresh timer

### Issue: DNS resolution fails

**Solution**:
- Verify network connectivity
- Check if `registrar.api.heidihealth.com` is accessible:
  ```bash
  ping registrar.api.heidihealth.com
  curl https://registrar.api.heidihealth.com/api/v2/ml-scribe/open-api/jwt
  ```

---

## 6. References

- **Official Documentation**: https://www.heidihealth.com/developers
- **API Key**: Obtain from Heidi Developer Portal
- **Support**: Contact Heidi Health support for API access issues

---

**Last Updated**: 2025-11-29
**Status**: Verified and tested with current implementation
