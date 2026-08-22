# OpenChemDb

OpenChemDb is a high-performance chemical data platform featuring a FastAPI backend, a modern frontend, and dual PostgreSQL databases enhanced with the RDKit cartridge for chemical informatics.

## Architecture Overview

The project uses a split-database architecture:
* **Users DB**: Stores user profiles and personal chemical data.
* **Archive DB**: A high-capacity database designed to handle ~3 million public chemical reactions.
* **App**: FastAPI backend with Uvicorn/Gunicorn.
* **Frontend**: Modern web interface served via Caddy.

---

## ⚡ Quick Start with Makefile (Docker Compose)

The easiest way to orchestrate the application locally is by using the provided `Makefile`. 

### Prerequisites
Before running the commands, ensure you have installed:
1. **Docker & Docker Compose**
2. **GNU Make** (On Windows, install via `winget install ezwinports.make` or `scoop install make`)

### Environment Setup
First, create your local environment file:
```bash
cp .env.example .env
```

### Commands Reference

| Action | Command | Description                                                                                                                                                       |
|---|---|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Start** | `make up` | Standard launch of the local environment in the background.  Open http://localhost:8080/ to see the interface.                                                    |
| **Update** | `make update` | Rebuilds the app and frontend builder without cache, restarts containers, waits for databases to pass healthchecks, and automatically applies Alembic migrations. |
| **Stop** | `make down` | Safely stops and removes local containers without losing named volumes.                                                                                           |

### 📦 Public Database Dump & Initial Setup

If you need the full public reaction database (~3 million reactions) in addition to your personal entry log, follow these steps:

#### 1. Download and Extract
1. Download the database dump archive: https://data.openchemdb.com/database-dump/data.7z
2. Extract the archive into your project root directory. This will create the `./data/` folder.

#### 2. First-Time Setup Process
Importing and initializing 3 million reactions in PostgreSQL can take **up to 5 hours** depending on your hardware. To prevent the application containers from timing out while the database is initializing, follow this sequence:

* **Step A (Start Database Initialization):**

  make init-db

  *Monitor the progress of the dump import using:* `docker compose logs -f archive_db`

* **Step B (Spin Up Main Services):**
  Once `archive_db` finishes initializing and reports a healthy status, start the remaining application containers:

  make up

* **Step C (Build Frontend & Run Migrations):**

  make update

> 💡 **Shortcut:** Once `archive_db` is fully initialized and healthy, you can run steps **B** and **C** together with a single command:
>
> make first-start

> ⚠️ **If you accidentally ran `make up` BEFORE extracting the dump:**
> 1. Stop the running containers: `make down`
> 2. Delete the created empty database directory: `rm -rf data/archive`
> 3. Extract `data.7z` into the project root directory.
> 4. Start initialization: `make init-db`

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
sudo chown -R 999:999 ./data

# Build and start all services
docker compose up --build

#run migrations on database
docker compose exec app alembic upgrade head
```