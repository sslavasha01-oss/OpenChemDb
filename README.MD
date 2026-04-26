# OpenChemDb

OpenChemDb is a high-performance chemical data platform featuring a FastAPI backend, a modern frontend, and dual PostgreSQL databases enhanced with the RDKit cartridge for chemical informatics.

## Architecture Overview

The project uses a split-database architecture:
* **Users DB**: Stores user profiles and personal chemical data.
* **Archive DB**: A high-capacity database designed to handle ~3 million public chemical reactions.
* **App**: FastAPI backend with Uvicorn/Gunicorn.
* **Frontend**: Modern web interface served via Caddy.

---

## Development Setup

Follow these steps to set up the project locally for development.

### 1. Prerequisites

Ensure you have the following installed:
* **Docker & Docker Compose**
* **Python 3.12**
* **Node.js & npm** (for frontend development)

### 2. Environment Configuration

Rename the example environment file and adjust the variables if necessary:

```bash
# In the project root
cp .env.example .env
```

Build and start the databases:

```Bash
docker compose up -d users_db archive_db
```

### 4. Backend Setup

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Unix:
   source venv/bin/activate
   #install requirements
   pip install -r requirements.txt
   ```
   
2. **Run Migrations (Alembic)**
Make sure your databases are running in Docker, then apply migrations:

```Bash
alembic upgrade head
```
3. **Start Backend in Dev Mode:**

```Bash
# Execute from the project root
uvicorn app.main:app --reload
```
The API will be available at http://localhost:8000
Swagger: http://localhost:8000/docs#/

### 5. Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```
2. Install dependencies and run:

```Bash
npm install
npm run dev
```

The frontend will be available at the address shown in your terminal (usually http://localhost:5173

# Running with Docker (Production-like)
If you want to spin up the entire stack (including Caddy and the built frontend):

```Bash
#Set permissions for the data directory (Linux/macOS)
sudo chown -R 1000:1000 ./data

# Build and start all services
docker compose up --build

#run migrations on database
docker compose exec app alembic upgrade head
```