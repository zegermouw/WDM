docker build ./payment -t mwschutte/payment:latest 
docker push mwschutte/payment:latest
kubectl rollout restart -n default deployment payment-deployment