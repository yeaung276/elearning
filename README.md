# E-Learning Platform

## Environment

| Property | Value |
|---|---|
| **Operating System** | macOS |
| **Python Version** | >= 3.12 |
| **Django Version** | 6.0 |

---

## Installation

### Docker (Recommended)

It is highly recommended to run the entire stack using Docker. A `docker-compose.yaml` and respective build files are provided.

```bash
docker-compose up
```

This will spin up **Redis**, **Web**, and **Celery** all together.

### Standalone

In standalone mode, Celery will not work because Redis is not available — only the web server runs. Live messaging will fall back to an in-memory channel layer instead of Redis.

1. Install dependencies:
   ```bash
   uv sync
   ```
2. Run the server (databases are already migrated and populated with mock data):
   ```bash
   uv run manage.py runserver
   ```

---

## Credentials

### Students

| Username | Password |
|---|---|
| `student1` | `Password123!@#` |
| `student2` | `Password123!@#` |
| `student3` | `Password123!@#` |

### Teachers

| Username | Password |
|---|---|
| `teacher1` | `Password123!@#` |
| `teacher2` | `Password123!@#` |
| `teacher3` | `Password123!@#` |

### Admin

| Username | Password |
|---|---|
| `admin` | `admin` |
