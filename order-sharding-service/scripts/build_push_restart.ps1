docker build ./order-sharding-service -t markodorko/order-sharding
docker push markodorko/order-sharding
kubectl rollout restart -n default deployment order-sharding-deployment
