revisar el .env.example

source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

pip install -r requirements.txt

python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

1. Eliminas todos los archivos de versions/
2. alembic revision --autogenerate -m "initial"
3. alembic upgrade head

uvicorn main:app --reload --port 8000

con eso el proyecto puede funcionar