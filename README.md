# College Assistant

A smart, contextual chatbot and portal built with React, FastAPI, and LangGraph. The College Assistant provides students with quick access to academic information, while letting admins manage records and view usage statistics.

## Features

- **Conversational RAG**: Intelligent question answering over academic documents using LangGraph and Groq's Llama models.
- **Live Student Data**: Answers queries about personal attendance, exam eligibility, and daily timetables directly from the live SQLite database.
- **Admin Dashboard**: Specialized interface for admins to manage student data, upload attendance records, and view analytics.
- **Persistent Chat History**: Saves conversation history per-user, allowing students to seamlessly pick up where they left off.
- **Modern UI**: Responsive React frontend with Vite for fast development and builds.
- **RESTful API**: FastAPI backend with clean, documented endpoints for all operations.

## Architecture

- **Frontend**: React 19 with Vite, TypeScript, React Router, and Recharts for visualizations
- **Backend**: FastAPI with LangChain and LangGraph for RAG and workflow orchestration
- **Workflow Engine**: LangGraph (`StateGraph`) for stateful, conditional routing of student queries
- **LLM / Embeddings**: Groq (Llama-based models), HuggingFace (`all-MiniLM-L6-v2`)
- **Database**: SQLite (`db.py`) for managing students, attendance, marks, and configuration
- **Containerization**: Docker and Docker Compose for easy deployment

## Setup and Installation

### Prerequisites
- Python 3.9+
- Node.js 16+ and npm
- Docker and Docker Compose (for containerized deployment)

### 1. Clone the repository:
```bash
git clone <your-repo-url>
cd college
```

### 2. Environment Variables:
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here
ADMIN_EMAILS=admin@college.edu,anotheradmin@college.edu
```

### 3. Backend Setup:

**Set up a virtual environment (recommended):**
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

### 4. Frontend Setup:

```bash
cd frontend
npm install
```

### 5. Initialize Dummy Data:
To populate your system with initial timetables and dummy students/attendance:
```bash
cd data
python create_data.py
```

## Docker Setup

### Prerequisites
- Docker (v20.10+)
- Docker Compose (v1.29+)

### Building Docker Images

**Build both services:**
```bash
docker-compose build
```

**Build specific service:**
```bash
# Backend only
docker-compose build backend

# Frontend only
docker-compose build frontend
```

### Running with Docker

**Start all services:**
```bash
docker-compose up -d
```

**Start with logs:**
```bash
docker-compose up
```

**Stop all services:**
```bash
docker-compose down
```

**View service logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Docker Development Workflow

**Rebuild after code changes:**
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

**Access running containers:**
```bash
# Backend shell
docker exec -it college_backend bash

# Frontend shell
docker exec -it college_frontend sh
```

**Remove all data and start fresh:**
```bash
docker-compose down -v
docker-compose up -d
```

### Docker Files Reference

- **backend/Dockerfile**: Builds Python FastAPI application
  - Uses Python slim image
  - Installs dependencies from requirements.txt
  - Runs uvicorn server on port 8000

- **frontend/Dockerfile**: Builds React application
  - Uses Node.js for build
  - Runs Nginx to serve static files on port 80
  - Optimized with multi-stage build

## Running the Application

### Development Mode:

**Terminal 1 - Start the Backend:**
```bash
cd backend
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Start the Frontend:**
```bash
cd frontend
npm run dev
```

The application will be available at:
- **Frontend**: http://localhost:5173 (Vite dev server)
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)

### Quick Start with Docker:

```bash
docker-compose up -d
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000

## Deployment (Docker / VPS)

For persistent storage (SQLite database and chat history), Docker is the recommended deployment method on a Virtual Private Server (AWS EC2, DigitalOcean, Linode, etc.).

### Deployment Steps:

1. Ensure your server has Docker and Docker Compose installed.
2. Clone your repository onto the server.
3. Setup your `.env` file on the server with production values.
4. From the root directory, run:
   ```bash
   docker-compose up -d
   ```

### Access Points:

- **Frontend**: http://your-domain.com (via Nginx on port 3000)
- **Backend API**: http://your-domain.com/api (proxy to port 8000)

### Reverse Proxy Setup (Recommended):

If you want to serve both frontend and backend from a single domain, set up Nginx or Caddy to reverse proxy:
- Port 3000 → Frontend
- Port 8000 → Backend API

### Data Persistence:

The `docker-compose.yml` is configured to mount the `./data` directory as a volume. This ensures:
- Student attendance records
- Chat histories
- Configuration data
- All data persists across container restarts

## Project Structure

```
college/
├── backend/                    # FastAPI backend
│   ├── main.py                # Entry point
│   ├── admin.py               # Admin operations
│   ├── auth.py                # Authentication logic
│   ├── chat.py                # Chat/RAG endpoints
│   ├── student.py             # Student data endpoints
│   ├── db.py                  # SQLite database management
│   ├── requirements.txt        # Python dependencies
│   └── Dockerfile             # Backend container config
├── frontend/                   # React + Vite frontend
│   ├── src/
│   │   ├── App.jsx            # Main app component
│   │   ├── main.jsx           # Entry point
│   │   ├── api.js             # API client
│   │   ├── components/        # Reusable components
│   │   └── pages/             # Page components
│   ├── package.json           # Node dependencies
│   ├── vite.config.js         # Vite configuration
│   └── Dockerfile             # Frontend container config
├── data/                       # Data files and utilities
│   ├── create_data.py         # Dummy data generation
│   ├── academic_calendar.json # Academic schedule
│   ├── timetable.json         # Class timetables
│   ├── feedback.jsonl         # User feedback logs
│   ├── interactions.jsonl     # Chat interaction logs
│   └── chat_history/          # Per-user chat histories
├── docker-compose.yml         # Multi-container orchestration
├── .env                       # Environment variables (create this)
└── README.md                  # This file
```

## Environment Variables

Required `.env` file in the project root:

```env
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional
ADMIN_EMAILS=admin@college.edu,anotheradmin@college.edu
```

Get your Groq API key from: https://console.groq.com/

## API Documentation

When running the backend locally or in Docker, access the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Troubleshooting

### Backend Issues

**ImportError: No module named 'X'**
- Make sure you've activated the virtual environment and installed requirements:
  ```bash
  cd backend
  source venv/bin/activate  # or .\venv\Scripts\activate on Windows
  pip install -r requirements.txt
  ```

**Connection refused on port 8000**
- Check if another process is using port 8000:
  ```bash
  # On Windows: netstat -ano | findstr :8000
  # On macOS/Linux: lsof -i :8000
  ```

### Frontend Issues

**Module not found errors**
- Clear node_modules and reinstall:
  ```bash
  cd frontend
  rm -rf node_modules package-lock.json  # or del node_modules on Windows
  npm install
  ```

**Port 3000 already in use**
- Modify Vite config or use a different port:
  ```bash
  npm run dev -- --port 3001
  ```

### Docker Issues

**Container won't start**
- Check logs:
  ```bash
  docker-compose logs backend
  docker-compose logs frontend
  ```

**Port conflicts**
- Edit `docker-compose.yml` to use different ports (e.g., `8001:8000` for backend)

**Permission denied on Linux**
- Add your user to docker group:
  ```bash
  sudo usermod -aG docker $USER
  newgrp docker
  ```

**Out of disk space**
- Clean up unused Docker resources:
  ```bash
  docker system prune -a
  docker volume prune
  ```

**Changes not reflecting in container**
- Rebuild the image:
  ```bash
  docker-compose down
  docker-compose build --no-cache
  docker-compose up -d
  ```

**Volumes not syncing**
- On Windows/Mac with Docker Desktop, volumes may need configuration
- Check Docker Desktop settings: File Sharing / Resources
- Ensure paths are shared: `C:\projects\college` (Windows) or `/path/to/college` (Mac/Linux)

**Backend can't connect to files**
- Verify volumes in `docker-compose.yml`:
  ```yaml
  volumes:
    - ./data:/app/data
    - ./.env:/app/.env:ro
  ```

**Frontend can't reach backend API**
- Check that both containers are on the same network:
  ```bash
  docker network ls
  docker network inspect college_default
  ```
- Verify `FRONTEND_URL` environment variable in docker-compose.yml

## License

[Add your license here]

## Support

For issues or questions, please open an issue on the repository.
