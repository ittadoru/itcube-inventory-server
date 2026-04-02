# Server (IT Cube Inventory)

Содержимое этой папки полностью самодостаточно для запуска серверной части.

## Состав

- `app/` — FastAPI backend (API + admin panel)
- `requirements.txt` — python зависимости
- `Dockerfile` — сборка API-контейнера
- `docker-compose.yml` — API + PostgreSQL
- `.env.example` — пример переменных окружения
- `.gitignore` — игнор для серверного репозитория

## Запуск через Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

После запуска:

- API docs: `http://localhost:8000/docs`
- Админ-панель: `http://localhost:8000/admin`

## Локальный запуск без Docker

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
