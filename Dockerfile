FROM python:3.8-slim AS exporter

RUN pip install poetry
ADD . /repo
WORKDIR /repo
RUN poetry export --with=docker --output=requirements.txt

FROM python:3.8-slim

ENV r=/botanist

RUN apt-get update && apt-get install -y \
    git \
    mercurial \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p \
    ${r}/bin \
    ${r}/repos \
    ${r}/repos/.index \
    ${r}/repos/bitbucket \
    ${r}/repos/github

ENV CSEARCHINDEX=${r}/repos/.index

ADD packages/codesearch-0.01-linux-amd64.tgz ${r}/bin
ADD packages/bitbucket-backup.tgz ${r}/bin
ADD packages/github_backup.py ${r}/bin
ADD cron/index.sh ${r}/bin/index.sh
ADD cron/fetch-code.sh ${r}/bin/fetch-code.sh

COPY --from=exporter /repo/requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt
ADD ./webapp /code

VOLUME ${r}/repos

RUN groupadd -r botanist -g 9009 && useradd -u 9009 -g 9009 --no-log-init -r -g botanist botanist
RUN chown -R botanist:botanist ${r}
USER botanist

CMD uwsgi --socket :9090 --chdir /code --wsgi-file /code/codesearch/wsgi.py --master --processes 4 --threads 2 --buffer-size 65535
