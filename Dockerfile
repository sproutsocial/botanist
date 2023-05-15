# syntax=docker/dockerfile:1-labs
# using labs to get ADD git repo support
FROM golang:1.20 AS codesearch

ADD https://github.com/google/codesearch.git#v1.2.0 /codesearch
WORKDIR /codesearch
RUN go build ./cmd/cgrep
RUN go build ./cmd/cindex
RUN go build ./cmd/csearch

FROM python:3.11-slim

ENV r=/botanist

RUN apt-get update && apt-get install -y \
    git \
    mercurial \
    uwsgi-plugin-python3 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p \
    ${r}/bin \
    ${r}/repos \
    ${r}/repos/.index \
    ${r}/repos/bitbucket \
    ${r}/repos/github

ENV CSEARCHINDEX=${r}/repos/.index

COPY --link --from=codesearch /codesearch/cgrep /codesearch/cindex /codesearch/csearch ${r}/bin/
ADD packages/bitbucket-backup.tgz ${r}/bin
ADD packages/github_backup.py ${r}/bin
ADD cron/index.sh ${r}/bin/index.sh
ADD cron/fetch-code.sh ${r}/bin/fetch-code.sh

ADD webapp/requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt
ADD ./webapp /code

VOLUME ${r}/repos

ARG BOTANIST_UID=9009
RUN groupadd -r botanist -g ${BOTANIST_UID} && useradd -u ${BOTANIST_UID} -g ${BOTANIST_UID} --no-log-init -r -g botanist botanist
RUN chown -R botanist:botanist ${r}
USER botanist

CMD uwsgi --socket :9090 --chdir /code --wsgi-file /code/codesearch/wsgi.py --master --processes 4 --threads 2 --buffer-size 65535
