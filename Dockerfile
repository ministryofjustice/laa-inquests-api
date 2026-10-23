ARG BASE_IMAGE=python:3.12-slim
FROM $BASE_IMAGE AS base

ARG REQUIREMENTS=requirements-production.txt

# Create a non-root user
RUN adduser --disabled-password app -u 1000 && \
    cp /usr/share/zoneinfo/Europe/London /etc/localtime

RUN mkdir /home/app/laa-inquests-api
WORKDIR /home/app/laa-inquests-api

COPY requirements/system-packages.txt /tmp/system-packages.txt
RUN apt-get update && \
    apt-get install -y --no-install-recommends --only-upgrade \
        ca-certificates libsqlite3-0 perl-base gzip libpcre2-8-0 && \
    grep -vE '^\s*(#|$)' /tmp/system-packages.txt | \
        xargs apt-get install -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/* /tmp/system-packages.txt

COPY requirements/generated/$REQUIREMENTS requirements.txt
# TEMPORARY! Remove once pip >26.2.2 released, hash-pinned install to avoid certificate vulnerability by installing exact recommended version:
RUN pip install "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"
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
