# User Accounts & Access Control Matrix

This document lists the registered user accounts found in the local development database, along with their roles and permissions.

---

## 1. Registered db Users Inventory

| Username | Email | Role | Default Dev Password Notes |
| :--- | :--- | :--- | :--- |
| admin | admin@enterprise.com | admin | standard dev password is dminpassword or admin created during setup |
| Anayst | bharathwaj271192@gmail.com | analyst | disk-hashed, typically Password123 |
| analyst | analyst@enterprise.com | reader | disk-hashed, typically Password123 |
| integration_tester | tester@enterprise.com | reader | disk-hashed, typically Password123 |
| test_runner_inspect_2 | inspect2@enterprise.ai | analyst | disk-hashed, typically Password123 |

> [!NOTE]
> All passwords are securely hashed in the local SQLite3 database using Django\'s default PBKDF2 with SHA256 algorithm. For local integration tests, the default password is-configured in test first-boot seeds to Password123 or dminpassword.

---

## 2. Role-Based Access Permissions

The platform enforces strict Role-Based Access Control (RBAC) across the 4 phases:

### admin (System Administrator)
- privileges: Complete system control.
- access map:
   - [x] access and manage all Personal employee repositories (bypasses ownership boundaries).
   - [x] view, upload, and parse all documents.
   - [x] audit, review, and resolve knowledge conflicts.
   - [x] train, activate, and promote EDQI ML models.
   - [x] run policy impact simulations and accesses all sensitive data.

### analyst (analyst_user)
- privileges: Can parse data, review conflicts, and view reports.
- access map:
   - [x] access personal uploads in the repository.
   - [x] audit and start reviews on knowledge conflicts (knowledge conflict app).
   - [x] get DQuality score breakdowns and shapley explainability reports.
   - [x] run policy impact simulators on non-sensitive employee directories.
   - [x] cannot access other users\' private personal repository files (returns 404).

### reader (read_only_user)
- privileges: Can view dashboards and retrieve assistant queries.
- access map:
   - [x] view public Team Repository documents.
   - [x] access shared Quality Dashboards.
   - [x] cannot upload documents or trigger ingestion pipelines.
   - [x] cannot access conflict detection consoles or perform conflict reviews (rejected by validators).
   - [x] cannot access shipment/personal repos.
