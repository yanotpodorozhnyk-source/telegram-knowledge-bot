FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
COPY bot.py .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python", "bot.py"]
