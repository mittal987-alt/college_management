FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

ENTRYPOINT ["sh", "-c", "mkdir -p /app/.streamlit && if [ -f /etc/secrets/secrets.toml ]; then cp /etc/secrets/secrets.toml /app/.streamlit/secrets.toml; fi && exec streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]