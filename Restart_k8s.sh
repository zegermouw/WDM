kubectl apply -f k8s/order-app.yaml
kubectl rollout restart -n default deployment order-deployment
kubectl apply -f k8s/stock-app.yaml
kubectl rollout restart -n default deployment stock-deployment
kubectl apply -f k8s/stock_updater.yaml
kubectl rollout restart -n default deployment stock-updater-deployment
kubectl apply -f k8s/payment-app.yaml
kubectl rollout restart -n default deployment payment-deployment
kubectl apply -f k8s/coordinator-app.yaml
kubectl rollout restart -n default deployment coordinator-deployment
kubectl apply -f k8s/order-sharding-service.yaml
sleep 20s
kubectl rollout restart -n default deployment order-sharding-deployment
