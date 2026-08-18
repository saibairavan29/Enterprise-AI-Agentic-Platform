# Database Schema Entity-Relationship (ER) Diagram

This document illustrates the base database schema for Version 1 of the Enterprise AI Decision Intelligence Platform.

## Mermaid ER Diagram

```mermaid
erDiagram
    USER ||--o{ DOCUMENT : "uploads"
    DOCUMENT ||--|| METADATA : "describes"

    USER {
        int id PK
        string username
        string email
        string password
        string role "admin | analyst | reader"
        string first_name
        string last_name
        string phone_number
        datetime created_at
        datetime updated_at
    }

    DOCUMENT {
        int id PK
        int uploaded_by_id FK "references USER.id"
        string file_path "Uploads/ path"
        string file_hash "Unique SHA-256 hash"
        string original_name
        bigint file_size "in bytes"
        string mime_type "detected MIME"
        string processing_status "pending | parsing | completed | failed"
        string validation_status "pending | clean | duplicate | incomplete | invalid | suspicious"
        datetime created_at
        datetime updated_at
    }

    METADATA {
        int id PK
        int document_id FK "references DOCUMENT.id"
        string extraction_source
        string author
        datetime creation_date
        datetime modified_date
        jsonb extracted_properties "custom parsed key-values"
        datetime created_at
        datetime updated_at
    }
```

---

## Entity Descriptions

### 1. User
Represents system operators. Role-based access control is evaluated using the `role` field:
- `admin`: Full system control.
- `analyst`: Can ingest files, view quality classifications, and simulate policy impact.
- `reader`: Read-only dashboard access.

### 2. Document
Tracks physical file records and ingestion statuses. The uniqueness of each file is enforced via the `file_hash` SHA-256 metric, which blocks redundant duplicate uploads.

### 3. Metadata
Contains document properties parsed during the ingestion pipelines. It maintains a 1-to-1 relationship with the Document, holding properties like authorship, system metadata, and unstructured metrics in a PostgreSQL `JSONB` structure.
