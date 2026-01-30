FROM python:3.11-slim

WORKDIR /app

# requirements.txt の正しい場所を指定
COPY docker/stm2-reader/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# src はルート直下にあるのでこう書く
COPY src ./src

CMD ["python", "src/stm2_reader_cli.py"]
