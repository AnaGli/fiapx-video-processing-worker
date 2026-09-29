# FIAP X — Video Processing Worker

Worker responsável pelo processamento assíncrono dos vídeos da solução FIAP X Video Processing.

O serviço recebe solicitações através do RabbitMQ, obtém o vídeo no storage S3-compatible, utiliza FFmpeg para extrair os frames, gera um arquivo ZIP com o resultado e publica um evento de sucesso ou falha.

---

## 1. Responsabilidades

O `video-processing-worker` é responsável por:

- consumir solicitações de processamento do RabbitMQ;
- registrar o processamento no seu próprio banco de dados;
- obter o vídeo no S3-compatible storage;
- processar o vídeo utilizando FFmpeg;
- extrair os frames;
- compactar os frames em um arquivo ZIP;
- armazenar o resultado no S3;
- registrar o resultado do processamento;
- publicar eventos de conclusão;
- publicar eventos de falha;
- permitir processamento concorrente através de múltiplas réplicas.

O Worker não acessa o banco de dados da API.

---

## 2. Arquitetura

```mermaid
flowchart LR
    Rabbit[RabbitMQ]
    Worker[Video Processing Worker]
    DB[(PostgreSQL\nvideo_processing)]
    S3[S3 / LocalStack]
    FFmpeg[FFmpeg]

    Rabbit -->|VideoProcessingRequested| Worker

    Worker -->|Processing Jobs| DB
    Worker -->|Get input video| S3
    S3 --> Worker

    Worker --> FFmpeg
    FFmpeg --> Worker

    Worker -->|Upload frames.zip| S3

    Worker -->|VideoProcessingCompleted| Rabbit
    Worker -->|VideoProcessingFailed| Rabbit
```

O Worker é independente da API.

A comunicação com o `video-management-api` ocorre exclusivamente através do RabbitMQ.

---

## 3. Stack

- Python 3.12
- RabbitMQ
- PostgreSQL
- SQLAlchemy
- Alembic
- boto3
- S3-compatible storage
- FFmpeg
- Docker
- Kubernetes
- GitHub Actions
- Datadog

---

## 4. Fluxo de processamento

```text
RabbitMQ
   │
   │ VideoProcessingRequested
   ▼
Worker
   │
   ├── cria processing job
   │
   ├── baixa vídeo do S3
   │
   ├── executa FFmpeg
   │
   ├── extrai frames
   │
   ├── gera frames.zip
   │
   ├── envia ZIP para S3
   │
   ├── registra resultado
   │
   └── publica evento
             │
             ├── Completed
             │
             └── Failed
```

O processamento é desacoplado da requisição HTTP original.

---

## 5. Mensagem de entrada

A API publica no RabbitMQ:

```text
VideoProcessingRequested
```

O Worker consome essa mensagem na fila:

```text
video-processing
```

Exemplo conceitual:

```json
{
  "event_type": "VideoProcessingRequested",
  "video_id": "uuid",
  "user_id": "uuid",
  "input_object_key": "videos/{video_id}/input/{filename}"
}
```

O Worker utiliza o `input_object_key` para localizar o vídeo no storage.

---

## 6. Processamento do vídeo

O processamento é realizado utilizando FFmpeg.

Fluxo interno:

```text
Input video
    │
    ▼
FFmpeg
    │
    ▼
Frames
    │
    ▼
ZIP
    │
    ▼
frames.zip
```

Os frames são gerados no diretório temporário configurado para o processamento.

Depois da criação do ZIP, o resultado é enviado para o storage.

---

## 7. Storage

O Worker utiliza um storage compatível com S3.

No ambiente local:

```text
LocalStack
```

Bucket:

```text
videos
```

### Entrada

```text
videos/{video_id}/input/{filename}
```

### Saída

```text
videos/{video_id}/output/frames.zip
```

A configuração do endpoint permite utilizar LocalStack durante o desenvolvimento sem alterar o fluxo lógico do serviço.

---

## 8. Banco de dados

O Worker possui seu próprio PostgreSQL:

```text
video_processing
```

O banco é separado do banco utilizado pela API.

Arquitetura:

```text
API
 │
 └── video_management DB

Worker
 │
 └── video_processing DB
```

O Worker nunca atualiza diretamente os registros de vídeos da API.

O resultado é comunicado através de eventos RabbitMQ.

---

## 9. Processing Jobs

O Worker mantém informações relacionadas à execução do processamento.

Entre os dados utilizados pelo processamento estão:

- identificação do vídeo;
- estado do processamento;
- informações do resultado;
- quantidade de frames;
- mensagem de erro quando ocorre uma falha;
- timestamps relacionados ao processamento.

A mensagem de erro possui armazenamento como `TEXT`, permitindo registrar erros extensos provenientes de ferramentas como FFmpeg.

---

## 10. Eventos de saída

Depois do processamento, o Worker publica um dos dois eventos.

### Sucesso

```text
VideoProcessingCompleted
```

Exemplo:

```json
{
  "event_type": "VideoProcessingCompleted",
  "video_id": "uuid",
  "user_id": "uuid",
  "output_object_key": "videos/{video_id}/output/frames.zip",
  "frame_count": 150
}
```

A API recebe esse evento e atualiza o vídeo para:

```text
COMPLETED
```

### Falha

```text
VideoProcessingFailed
```

Exemplo:

```json
{
  "event_type": "VideoProcessingFailed",
  "video_id": "uuid",
  "user_id": "uuid",
  "error_message": "FFmpeg failed: ..."
}
```

A API recebe esse evento e atualiza o vídeo para:

```text
FAILED
```

---

## 11. RabbitMQ

Filas utilizadas:

```text
video-processing
video-processing-completed
video-processing-failed
```

### Entrada

```text
video-processing
```

Consumida pelo Worker.

### Saída — sucesso

```text
video-processing-completed
```

### Saída — falha

```text
video-processing-failed
```

A criação das filas é realizada pela infraestrutura/API, enquanto o Worker utiliza as filas existentes.

Isso evita que múltiplas réplicas do Worker tenham que assumir a responsabilidade de criar a infraestrutura de mensageria.

---

## 12. Concorrência

O Worker foi projetado para permitir processamento de múltiplos vídeos.

A escalabilidade ocorre horizontalmente:

```text
             RabbitMQ
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
   Worker 1  Worker 2  Worker 3
       │         │         │
       ▼         ▼         ▼
    FFmpeg    FFmpeg    FFmpeg
```

Cada instância do Worker pode consumir mensagens da mesma fila.

Quando a quantidade de trabalho aumenta, o Kubernetes pode criar novas réplicas.

---

## 13. Kubernetes HPA

O Worker possui Horizontal Pod Autoscaler.

Configuração:

```text
Minimum replicas: 1
Maximum replicas: 10
CPU target:       70%
Memory target:    50%
```

Os recursos configurados para o container são:

```text
Requests:
  CPU:    250m
  Memory: 256Mi

Limits:
  CPU:    1
  Memory: 1Gi
```

Durante o teste de carga foi observado o escalonamento do Worker:

```text
1 replica
   ↓
carga aumenta
   ↓
CPU/memory acima dos targets
   ↓
HPA scale-up
   ↓
4 replicas
```

Esse comportamento permite distribuir o processamento entre múltiplas instâncias.

---

## 14. Teste de carga

Foi realizado teste com múltiplos uploads simultâneos.

Exemplo de resultado:

```text
Concurrent uploads: 5

Upload phase: 1.07s

Processing:
video-5.mp4 COMPLETED - 721 frames
video-4.mp4 COMPLETED - 150 frames
video-3.mp4 COMPLETED - 1603 frames
video-2.mov COMPLETED - 171 frames
video-1.mov COMPLETED - 171 frames

Processing phase: 18.36s

All 5 videos processed successfully

LOAD TEST PASSED
```

Durante a execução, o HPA do Worker chegou a:

```text
1 → 4 replicas
```

Esse teste demonstrou o processamento concorrente e o escalonamento horizontal do Worker.

---

## 15. Tratamento de falhas

Falhas de processamento não são tratadas como sucesso.

Exemplo:

```text
VideoProcessingRequested
        │
        ▼
     FFmpeg
        │
        X
     error
        │
        ▼
VideoProcessingFailed
```

O erro é registrado no banco do Worker e enviado para a API através do evento de falha.

A API então apresenta o vídeo como:

```text
FAILED
```

com a mensagem de erro disponível para consulta.

---

## 16. Exemplo de falha do FFmpeg

Durante os testes foi utilizado um arquivo inválido.

O fluxo observado foi:

```text
Upload
  ↓
RabbitMQ
  ↓
Worker
  ↓
FFmpeg
  ↓
Invalid data / processing error
  ↓
Processing Job = FAILED
  ↓
VideoProcessingFailed
  ↓
API
  ↓
Video = FAILED
```

A mensagem completa do FFmpeg é preservada para facilitar diagnóstico.

---

## 17. Estrutura da aplicação

Estrutura principal:

```text
app/
├── core/
│   └── config.py
│
├── dependencies/
│   └── database.py
│
├── messaging/
│   ├── events.py
│   └── rabbitmq.py
│
├── models/
│   ├── base.py
│   └── processing_job.py
│
├── repositories/
│   └── processing_job_repository.py
│
├── services/
│   ├── processing_service.py
│   ├── storage_service.py
│   └── video_processor.py
│
└── main.py
```

### Responsabilidades

#### `processing_service.py`

Orquestra o processamento completo:

```text
event
 ↓
processing job
 ↓
storage
 ↓
video processor
 ↓
storage
 ↓
result event
```

#### `video_processor.py`

Responsável pela operação do FFmpeg e geração dos frames/ZIP.

#### `storage_service.py`

Abstrai as operações no S3-compatible storage.

#### `processing_job_repository.py`

Responsável pela persistência dos jobs de processamento.

#### `rabbitmq.py`

Gerencia comunicação com o RabbitMQ.

#### `events.py`

Define os contratos/eventos utilizados na comunicação.

---

## 18. Migrações

O banco do Worker utiliza Alembic para versionamento do schema.

Comando para aplicar migrations:

```bash
alembic upgrade head
```

As migrations fazem parte do repositório.

Isso permite reproduzir a estrutura do banco em diferentes ambientes.

---

## 19. Configuração

Principais variáveis de ambiente:

### Database

```text
DATABASE_URL
```

### RabbitMQ

```text
RABBITMQ_HOST
RABBITMQ_PORT
RABBITMQ_USERNAME
RABBITMQ_PASSWORD
RABBITMQ_INPUT_QUEUE
RABBITMQ_COMPLETED_QUEUE
RABBITMQ_FAILED_QUEUE
```

### S3

```text
S3_ENDPOINT_URL
S3_ACCESS_KEY_ID
S3_SECRET_ACCESS_KEY
S3_REGION
S3_BUCKET
```

### Processing

```text
STORAGE_PATH
```

Exemplo utilizado no Kubernetes:

```text
DATABASE_URL=postgresql+psycopg://postgres:postgres@video-worker-db.video-infra.svc.cluster.local:5432/video_processing

RABBITMQ_HOST=rabbitmq.video-infra.svc.cluster.local
RABBITMQ_PORT=5672

S3_ENDPOINT_URL=http://localstack.video-infra.svc.cluster.local:4566
S3_BUCKET=videos

STORAGE_PATH=/tmp/video-processing
```

Credenciais devem ser fornecidas através de Kubernetes Secrets e não devem ser versionadas.

---

## 20. Docker

A imagem do Worker contém o runtime Python e o FFmpeg necessário para o processamento.

O container executa o processo do Worker diretamente.

O FFmpeg é uma dependência obrigatória da imagem porque o processamento ocorre dentro do container.

---

## 21. Kubernetes

O Worker possui manifests para:

```text
ConfigMap
Secret
Deployment
HPA
```

O Worker não precisa de um Kubernetes Service porque não recebe requisições HTTP de outros componentes.

Seu principal mecanismo de entrada é:

```text
RabbitMQ
```

A arquitetura é:

```text
RabbitMQ
    │
    ▼
Worker Deployment
    │
    ├── Pod
    ├── Pod
    ├── Pod
    └── ...
```

---

## 22. Deploy

O projeto possui script de deploy:

```bash
./deploy.sh
```

Os recursos principais podem ser verificados com:

```bash
kubectl get deployment video-processing-worker
kubectl get pods -l app=video-processing-worker
kubectl get hpa video-processing-worker-hpa
```

Para acompanhar o escalonamento:

```bash
kubectl get hpa -w
```

Para acompanhar os pods:

```bash
kubectl get pods -l app=video-processing-worker -w
```

Para observar consumo de recursos:

```bash
kubectl top pods -l app=video-processing-worker
```

---

## 23. Observabilidade

O Worker está integrado ao Datadog através da infraestrutura Kubernetes.

A observabilidade permite acompanhar:

- execução do Worker;
- chamadas ao PostgreSQL;
- operações no S3;
- traces;
- erros;
- comportamento durante processamento.

Exemplos de operações observadas incluem:

```text
psycopg.connection.rollback
s3.getobject
s3.headobject
```

Isso permite investigar o fluxo do processamento e identificar gargalos ou falhas de integração.

---

## 24. Testes

O Worker possui testes para os principais componentes:

### Video Processor

Testes de:

- processamento;
- extração;
- comportamento em diferentes cenários.

Cobertura do componente:

```text
100%
```

### Storage Service

Cobertura:

```text
100%
```

### Processing Service

Testes de:

- processamento com sucesso;
- eventos inválidos;
- tratamento de falhas.

Cobertura:

```text
81%
```

### Processing Job Repository

Cobertura:

```text
100%
```

### RabbitMQ

Testes de comunicação/mensageria:

```text
100%
```

### Cobertura geral

```text
85%
```

---

## 25. CI/CD

O Worker possui pipeline GitHub Actions.

Fluxo:

```text
Push / Pull Request
        │
        ▼
GitHub Actions
        │
        ├── Checkout
        │
        ├── Python 3.12
        │
        ├── Install dependencies
        │
        ├── Run tests
        │
        ├── Generate coverage
        │
        └── Validate coverage >= 80%
```

Exemplo da etapa de testes:

```yaml
- name: Run tests with coverage
  run: |
    pytest \
      --cov=app \
      --cov-report=term-missing \
      --cov-report=xml \
      --cov-fail-under=80
  env:
    PYTHONPATH: .
    DATABASE_URL: sqlite:///./test.db
```

A pipeline falha caso a cobertura fique abaixo de 80%.

---

## 26. Isolamento de banco

Uma decisão arquitetural importante é que API e Worker possuem bancos separados.

```text
┌─────────────────────────┐
│ Video Management API    │
│                         │
│ PostgreSQL              │
│ video_management        │
└────────────┬────────────┘
             │
             │ RabbitMQ
             │
┌────────────▼────────────┐
│ Video Processing Worker │
│                         │
│ PostgreSQL              │
│ video_processing        │
└─────────────────────────┘
```

Benefícios:

- baixo acoplamento entre serviços;
- independência de deploy;
- independência de escala;
- isolamento dos dados;
- ausência de acesso direto de um serviço ao banco do outro.

---

## 27. Por que o processamento é assíncrono?

O processamento de vídeo pode ser uma operação longa e consumir CPU.

Se fosse executado diretamente durante o request HTTP:

```text
HTTP request
    │
    ▼
FFmpeg
    │
    ▼
HTTP response
```

a API ficaria responsável por manter a requisição aberta durante todo o processamento.

Na arquitetura implementada:

```text
HTTP request
    │
    ▼
API
    │
    ▼
RabbitMQ
    │
    ▼
Worker
    │
    ▼
FFmpeg
```

A API fica desacoplada do tempo necessário para processar o vídeo.

---

## 28. Por que RabbitMQ?

O RabbitMQ funciona como buffer entre a entrada de solicitações e a capacidade de processamento.

```text
        uploads
           │
           ▼
      Video API
           │
           ▼
      RabbitMQ
           │
     ┌─────┼─────┐
     ▼     ▼     ▼
 Worker Worker Worker
```

Durante picos, as mensagens permanecem na fila enquanto novas instâncias do Worker podem ser criadas pelo Kubernetes.

Isso evita depender de uma relação direta:

```text
1 upload = 1 processamento imediato
```

e permite desacoplar a taxa de entrada da taxa de processamento.

---

## 29. Fluxo completo

```text
┌─────────────┐
│    Client   │
└──────┬──────┘
       │
       │ upload
       ▼
┌─────────────────────┐
│ Video Management API│
└──────────┬──────────┘
           │
           ├──────────────► S3
           │
           │ VideoProcessingRequested
           ▼
      ┌───────────┐
      │ RabbitMQ  │
      └─────┬─────┘
            │
            ▼
┌────────────────────────┐
│ Video Processing Worker│
└───────────┬────────────┘
            │
            ├──────────────► PostgreSQL
            │
            ├──────────────► S3
            │
            ▼
          FFmpeg
            │
            ▼
         frames.zip
            │
            ▼
          S3
            │
            │ Completed / Failed
            ▼
      ┌───────────┐
      │ RabbitMQ  │
      └─────┬─────┘
            │
            ▼
┌─────────────────────┐
│ Video Management API│
└─────────────────────┘
            │
            ▼
      Update status
```

---

## 30. Requisitos funcionais relacionados

| Requisito | Implementação |
|---|---|
| Processar mais de um vídeo simultaneamente | Múltiplas mensagens + múltiplas réplicas do Worker |
| Suportar picos | RabbitMQ como buffer |
| Não perder solicitações durante picos | Mensagens permanecem na fila até serem consumidas |
| Persistência | PostgreSQL próprio |
| Arquivos | S3-compatible storage |
| Processamento | FFmpeg |
| Escalabilidade | Kubernetes + HPA |
| Comunicação | RabbitMQ |
| Testes | Pytest |
| Qualidade | 85% de cobertura |
| CI/CD | GitHub Actions |
| Observabilidade | Datadog |

---

## 31. Comandos úteis

### Ver Worker

```bash
kubectl get pods -l app=video-processing-worker
```

### Logs

```bash
kubectl logs -l app=video-processing-worker --tail=100
```

### Acompanhar logs

```bash
kubectl logs -f -l app=video-processing-worker
```

### HPA

```bash
kubectl get hpa video-processing-worker-hpa
```

### Acompanhar HPA

```bash
kubectl get hpa -w
```

### Recursos

```bash
kubectl top pods -l app=video-processing-worker
```

### Eventos do Kubernetes

```bash
kubectl get events \
  --sort-by='.lastTimestamp' \
  -w
```

