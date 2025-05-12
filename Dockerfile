FROM 412335208158.dkr.ecr.us-east-1.amazonaws.com/python:3.11-slim AS exporter

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry
RUN poetry self add poetry-plugin-export
COPY pyproject.toml poetry.lock /tmp/
RUN poetry export -C /tmp --output=/tmp/requirements.txt

RUN python3 -m venv /venv \
    && /venv/bin/pip install uwsgi && /venv/bin/pip install --no-deps --compile -r /tmp/requirements.txt

FROM 412335208158.dkr.ecr.us-east-1.amazonaws.com/python:3.11-slim
LABEL com.sproutsocial.docker.base-image="412335208158.dkr.ecr.us-east-1.amazonaws.com/python:3.11-slim"

ENV r=/botanist

RUN apt-get update && apt-get install -y --no-install-recommends \
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

COPY --from=exporter /venv /venv

ADD ./webapp /code

VOLUME ${r}/repos

RUN groupadd -r botanist -g 9009 && useradd -u 9009 -g 9009 --no-log-init -r -g botanist botanist
RUN chown -R botanist:botanist ${r}
USER botanist

CMD /venv/bin/uwsgi --socket :9090 --chdir /code --virtualenv /venv --wsgi-file /code/codesearch/wsgi.py --master --processes 4 --threads 2 --buffer-size 65535 --enable-threads --py-call-uwsgi-fork-hooks
