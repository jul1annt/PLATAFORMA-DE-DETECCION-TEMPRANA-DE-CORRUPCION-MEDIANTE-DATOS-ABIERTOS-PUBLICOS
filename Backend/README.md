revisa el .env.example

python -m venv venv
venv\Scripts\activate

pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic pydantic pydantic-settings python-dotenv apscheduler requests cryptography

python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

1. Eliminas todos los archivos de versions/
2. alembic revision --autogenerate -m "initial"
3. alembic upgrade head

uvicorn main:app --reload --port 8000