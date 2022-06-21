docker build ./payment -t markodorko/payment:latest 
docker push markodorko/payment:latest
kubectl rollout restart -n default deployment payment-deployment