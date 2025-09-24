# Kubernetes Deployment

This directory contains Kubernetes manifests for deploying Purplex to a K8s cluster.

## Structure

- `namespace.yaml` - Purplex namespace
- `configmap.yaml` - Configuration data
- `secrets.yaml` - Sensitive data (not in repo)
- `deployment-django.yaml` - Django app deployment
- `deployment-celery.yaml` - Celery workers deployment
- `service.yaml` - Service definitions
- `ingress.yaml` - Ingress rules
- `hpa.yaml` - Horizontal Pod Autoscaler

## Deployment

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Create secrets (customize first)
kubectl apply -f secrets.yaml

# Deploy all resources
kubectl apply -f .

# Check status
kubectl get all -n purplex
```

## Notes

- Secrets should never be committed to version control
- Use sealed-secrets or external secret management
- Configure resource limits based on your cluster capacity
- Set up monitoring with Prometheus/Grafana