FROM python:3.13-slim AS builder

RUN pip install --upgrade pip poetry poetry-plugin-export

COPY pyproject.toml poetry.lock ./

RUN poetry export -f requirements.txt $EXPORT_FLAG --without-hashes --output /tmp/requirements.txt


FROM python:3.13-slim

RUN apt-get update && \
  apt upgrade -y

WORKDIR /app

RUN groupadd -g 10000 app && \
  useradd -g app -d /app -u 10000 app && \
  chown app:app /app && \
  apt-get update && \
  apt-get install nano && \
  pip install --upgrade pip

COPY --from=builder /tmp/requirements.txt .

COPY devops-toolbox/scripts/secrets-entrypoint.sh secrets-entrypoint.sh

RUN pip install -r requirements.txt

COPY . .

USER app

ENTRYPOINT [ "./secrets-entrypoint.sh" ]
CMD ["python", "./ikigai_whatsapp_bot/main.py"]
