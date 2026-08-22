# College Assistant

A smart, contextual chatbot and portal built with Streamlit and LangGraph. The College Assistant provides students with quick access to academic information, while letting admins manage records and view usage statistics.

## Features

- **Conversational RAG**: Intelligent question answering over the college's `academics_handbook.pdf` and `fee_structure.pdf` using LangGraph and Groq.
- **Live Student Data**: Answers queries about personal attendance, exam eligibility, and daily timetables directly from the live SQLite database.
- **Multilingual Support**: Supports responding in both English and Hindi.
- **Google Authentication**: Native Google sign-in (OIDC) integration via Streamlit.
- **Admin Dashboard**: Specialized view for admins to track query volume, review common questions, manage user feedback (👍/👎), and upload attendance and student rosters.
- **Persistent Chat History**: Saves conversation history to disk per-user, allowing students to seamlessly pick up where they left off.

## Architecture

- **Frontend/Backend**: Streamlit (`app.py`)
- **Workflow Engine**: LangGraph (`StateGraph`) for stateful, conditional routing of student queries
- **LLM / Embeddings**: Groq (Llama-based models), HuggingFace (`all-MiniLM-L6-v2`)
- **Database**: SQLite (`db.py`) for managing students, attendance, marks, and configuration

## Setup and Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd college
   ```

2. **Set up a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: .\venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ADMIN_EMAILS=admin@college.edu,anotheradmin@college.edu
   ```

5. **Google OAuth Configuration:**
   Create a `.streamlit/secrets.toml` file to configure Google Sign-In:
   ```toml
   [auth]
   redirect_uri = "http://localhost:8501/oauth2callback"
   cookie_secret = "a_random_secret_string"
   client_id = "your_google_oauth_client_id"
   client_secret = "your_google_oauth_client_secret"
   server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
   ```

6. **Initialize Dummy Data:**
   To populate your system with initial timetables and dummy students/attendance, run:
   ```bash
   python data/create_data.py
   ```

## Running the Application

Start the Streamlit application:

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser. Log in using a Google account to start chatting!

## Deployment (Docker / VPS)

For persistent storage (since this app uses a local SQLite database and saves chat history as JSON), the best way to deploy is using Docker on a Virtual Private Server (like AWS EC2, DigitalOcean, or Linode).

1. Ensure your server has Docker and Docker Compose installed.
2. Clone your repository onto the server.
3. Setup your `.env` and `.streamlit/secrets.toml` files on the server as mentioned in the Setup section.
4. From the root directory, run:
   ```bash
   docker-compose up -d
   ```
5. Your application will be running on port `8501`. If you want to put it behind a domain, we recommend setting up a reverse proxy like Nginx or Caddy pointing to port 8501.

*Note: The `docker-compose.yml` is configured to mount the `./data` directory as a volume. This ensures your students' attendance, marks, config variables, and chat histories are not lost when the container restarts.*
