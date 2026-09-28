#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "Erro: arquivo .env não encontrado. Copie .env.example para .env e preencha os valores."
  exit 1
fi

echo "Pré-requisito: a infraestrutura compartilhada (RabbitMQ, LocalStack) e o"
echo "banco de dados deste worker precisam já estar de pé no namespace 'video-infra'"
echo "(repositório video-infra-k8s)."
echo ""

echo "Criando/atualizando Secret do worker a partir do .env..."
kubectl delete secret video-processing-worker-secrets --ignore-not-found
kubectl create secret generic video-processing-worker-secrets --from-env-file=.env

echo "Rodando migrations..."
kubectl delete job video-processing-worker-migrate --ignore-not-found
kubectl apply -f k8s/migration-job.yaml
kubectl wait --for=condition=complete job/video-processing-worker-migrate --timeout=90s

echo "Aplicando ConfigMap..."
kubectl apply -f k8s/configmap.yaml

echo "Aplicando Deployment do worker..."
kubectl apply -f k8s/deployment.yaml

echo "Aplicando HPA..."
kubectl apply -f k8s/hpa.yaml

echo "Reiniciando pods do worker para garantir que pegam config/secret atualizados..."
kubectl rollout restart deployment video-processing-worker

echo "Deploy do worker concluído!"
