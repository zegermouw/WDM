docker build ./stock -t markodorko/stock:latest
docker push markodorko/stock:latest
kubectl rollout restart -n default deployment stock-deployment
