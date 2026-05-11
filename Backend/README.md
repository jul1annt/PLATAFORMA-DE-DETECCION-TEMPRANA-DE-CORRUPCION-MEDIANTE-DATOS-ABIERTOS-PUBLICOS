revisa el .env.example

python -m venv venv
venv\Scripts\activate

pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic pydantic pydantic-settings python-dotenv apscheduler requests cryptography

python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

alembic init database/migrations

alembic revision --autogenerate -m "crear tabla fuentes_datos"

alembic upgrade head

uvicorn main:app --reload --port 8000