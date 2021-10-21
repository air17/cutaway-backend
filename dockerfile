FROM python:slim-bullseye
WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN apt-get update
RUN apt-get install -y python3-dev default-libmysqlclient-dev build-essential
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY . /app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
