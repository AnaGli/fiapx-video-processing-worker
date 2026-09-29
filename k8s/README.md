# video-processing-worker (k8s)

Manifests do worker responsável por consumir vídeos da fila e extrair frames.

## Dependências externas

Este serviço **não** provisiona sua infraestrutura compartilhada. Antes de rodar `deploy.sh`, é preciso que o repositório [`video-infra-k8s`](../video-infra-k8s) já tenha sido aplicado — ele sobe RabbitMQ e LocalStack no namespace `video-infra`.

O único recurso de infraestrutura que este repositório provisiona é o **Postgres exclusivo do worker** (`postgres.yaml`), que não é compartilhado com nenhum outro serviço.

## Uso

```bash
cp .env.example .env
# preencha DB_USER, DB_PASSWORD, RABBITMQ_USER, RABBITMQ_PASSWORD,
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
# (as credenciais do RabbitMQ/S3 devem bater com o que foi configurado em video-infra-k8s)

./deploy.sh
```

## Arquivos

```
configmap.yaml    # configuração não sensível (aponta para video-infra via DNS)
postgres.yaml      # banco de dados exclusivo do worker
deployment.yaml     # o worker em si
hpa.yaml            # autoscaling horizontal
.env.example
deploy.sh
```

## O que foi removido deste repositório

- `rabbitmq.yaml` / `localstack.yaml` — movidos para `video-infra-k8s`, pois são compartilhados com a API
- `service.yaml` — o worker não expõe endpoint HTTP (consumidor de fila), então não precisa de Service
- `metrics.yaml` (metrics-server) — é um add-on de cluster, não pertence a nenhum serviço específico; deve ser aplicado uma única vez por cluster, fora do ciclo de deploy de qualquer microsserviço
