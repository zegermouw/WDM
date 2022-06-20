docker build .\stock -t mwschutte/stock:latest
docker push mwschutte/stock:latest
kubectl rollout restart -n default deployment stock-deployment
