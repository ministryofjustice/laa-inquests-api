ARG BASE_IMAGE=python:3.12-slim
FROM $BASE_IMAGE AS base

ARG REQUIREMENTS=requirements-production.txt

# Create a non-root user
RUN adduser --disabled-password app -u 1000 && \
    cp /usr/share/zoneinfo/Europe/London /etc/localtime

# Install system dependencies required by WeasyPrint
# TODO: Use the requirements file to install dependencies instead of hardcoding them here
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    shared-mime-info && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir /home/app/laa-inquests-api
WORKDIR /home/app/laa-inquests-api

COPY requirements/generated/$REQUIREMENTS requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY app ./app
COPY bin ./bin
COPY alembic.ini ./alembic.ini

# Change ownership of the working directory to the non-root user
RUN chown -R app:app /home/app

# Switch to the non-root user
USER app

# Expose the fast api port
EXPOSE 8027

CMD ["uvicorn", "app:api", "--port",  "8027", "--host", "0.0.0.0"]
