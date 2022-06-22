
docker build .\stock_update_service -t mwschutte/stock-updater:latest
docker push mwschutte/stock-updater:latest
kubectl rollout restart -n default deployment stock-updater-deployment