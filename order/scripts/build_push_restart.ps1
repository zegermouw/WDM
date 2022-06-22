docker build ./order -t markodorko/order:latest 
docker push markodorko/order:latest
kubectl rollout restart -n default deployment order-deployment
kubectl rollout restart -n default deployment order-sharding-deployment