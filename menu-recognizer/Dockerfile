# Use the official Python image.
# https://hub.docker.com/_/python
FROM python:3.8

# Allow statements and log messages to immediately appear in the Cloud Run logs
ENV PYTHONUNBUFFERED True

# Install system tesseract, because pytesseract is only a wrapper
RUN apt-get update && apt-get install -y libgl1-mesa-dev tesseract-ocr libtesseract-dev tesseract-ocr-deu

# Install production dependencies.
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir pipenv

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

RUN pipenv install --system --deploy
# Install spacy model
RUN python -m spacy download de_core_news_sm

# Run the web service on container startup.
# Use gunicorn webserver with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app