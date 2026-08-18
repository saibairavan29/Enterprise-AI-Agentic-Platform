# API Contract Specifications

All API endpoints are version-controlled and run under the `/api/v1/` prefix. Every API response returns a consistent JSON payload structure.

---

## Global Response Format

### Successful Response Layout (HTTP 200 OK / 201 Created)
```json
{
  "success": true,
  "status_code": 200,
  "message": "Request completed successfully.",
  "data": {},
  "errors": [],
  "timestamp": "2026-07-28T11:23:45.123456Z"
}
```

### Error Response Layout (HTTP 400 / 401 / 403 / 500)
```json
{
  "success": false,
  "status_code": 400,
  "message": "Validation failed for one or more fields.",
  "data": {},
  "errors": {
    "username": ["This field is required."]
  },
  "timestamp": "2026-07-28T11:23:45.123456Z"
}
```

---

## API Endpoints

### 1. User Registration
Onboard new platform operators.
- **Endpoint**: `POST /api/v1/auth/register/`
- **Authentication**: None (`AllowAny`)
- **Request Body**:
  ```json
  {
    "username": "johndoe",
    "email": "johndoe@enterprise.ai",
    "password": "securepassword123",
    "password_confirm": "securepassword123",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "1234567890",
    "role": "analyst"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "success": true,
    "status_code": 201,
    "message": "User registered successfully.",
    "data": {
      "username": "johndoe",
      "email": "johndoe@enterprise.ai",
      "role": "analyst"
    },
    "errors": [],
    "timestamp": "2026-07-28T11:23:45.123456Z"
  }
  ```

---

### 2. User Login (Retrieve JWT Tokens)
Verify credentials and retrieve access/refresh tokens.
- **Endpoint**: `POST /api/v1/auth/login/`
- **Authentication**: None (`AllowAny`)
- **Request Body**:
  ```json
  {
    "username": "johndoe",
    "password": "securepassword123"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "status_code": 200,
    "message": "Credentials verified and token issued.",
    "data": {
      "access": "eyJhbGciOi...",
      "refresh": "eyJhbGciOi...",
      "user": {
        "id": 1,
        "username": "johndoe",
        "email": "johndoe@enterprise.ai",
        "role": "analyst",
        "phone_number": "1234567890"
      }
    },
    "errors": [],
    "timestamp": "2026-07-28T11:23:45.123456Z"
  }
  ```

---

### 3. Rotate Access Token
Submit a refresh token to request a new access token.
- **Endpoint**: `POST /api/v1/auth/login/refresh/`
- **Authentication**: None (`AllowAny`)
- **Request Body**:
  ```json
  {
    "refresh": "eyJhbGciOi..."
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "status_code": 200,
    "message": "Access token rotated successfully.",
    "data": {
      "access": "eyJhbGciOi..."
    },
    "errors": [],
    "timestamp": "2026-07-28T11:23:45.123456Z"
  }
  ```

---

### 4. Get User Profile
Retrieve profile details of the authenticated requester.
- **Endpoint**: `GET /api/v1/auth/profile/`
- **Authentication**: JWT Required (`IsAuthenticated`)
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "status_code": 200,
    "message": "Profile retrieved successfully.",
    "data": {
      "id": 1,
      "username": "johndoe",
      "email": "johndoe@enterprise.ai",
      "first_name": "John",
      "last_name": "Doe",
      "role": "analyst",
      "phone_number": "1234567890",
      "created_at": "2026-07-28T11:00:00Z"
    },
    "errors": [],
    "timestamp": "2026-07-28T11:23:45.123456Z"
  }
  ```

---

### 5. Update User Profile
Perform partial modifications to the user's profile details.
- **Endpoint**: `PUT /api/v1/auth/profile/`
- **Authentication**: JWT Required (`IsAuthenticated`)
- **Request Body**:
  ```json
  {
    "first_name": "Johnny",
    "phone_number": "9999999999"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "status_code": 200,
    "message": "Profile updated successfully.",
    "data": {
      "id": 1,
      "username": "johndoe",
      "email": "johndoe@enterprise.ai",
      "first_name": "Johnny",
      "last_name": "Doe",
      "role": "analyst",
      "phone_number": "9999999999",
      "created_at": "2026-07-28T11:00:00Z"
    },
    "errors": [],
    "timestamp": "2026-07-28T11:23:45.123456Z"
  }
  ```

---

### 6. Health Check API
Retrieve status, release versioning, and test live database connectivity of PostgreSQL.
- **Endpoint**: `GET /api/v1/health/`
- **Authentication**: None (`AllowAny`)
- **Response (200 OK - Healthy)**:
  ```json
  {
    "success": true,
    "status_code": 200,
    "message": "System status check completed successfully.",
    "data": {
      "application": "Enterprise AI Decision Intelligence Platform",
      "version": "1.0.0",
      "database_connection": "healthy",
      "environment": "development"
    },
    "errors": [],
    "timestamp": "2026-07-28T11:23:45.123456Z"
  }
  ```

---

### 7. File Ingestion Upload
Upload a document stream to be parsed by MIME type dispatcher routers.
- **Endpoint**: `POST /api/v1/ingestion/upload/`
- **Authentication**: JWT Required (`IsAuthenticated`)
- **Request Body**: Multipart Form Data (`file` key containing binary stream)
- **Response (201 Created)**:
  ```json
  {
    "success": true,
    "status_code": 201,
    "message": "Document uploaded successfully.",
    "data": {
      "document_id": 12,
      "file_name": "report.pdf",
      "processing_status": "UPLOADED"
    },
    "errors": [],
    "timestamp": "2026-07-28T11:23:45.123456Z"
  }
  ```
