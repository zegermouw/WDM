
docker build .\stock_update_service -t mwschutte/stockupdater:latest
docker push mwschutte/stockupdater:latest
kubectl rollout restart -n default deployment stockupdater-deployment