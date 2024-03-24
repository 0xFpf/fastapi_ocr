FROM python:3.10.5-slim

WORKDIR /usr/src/app

COPY requirements.txt ./
COPY alembic.ini /usr/src/app/alembic.ini

RUN pip install --no-cache-dir -r requirements.txt

RUN alembic -c /usr/src/app/alembic.ini upgrade head

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
