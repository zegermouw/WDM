minikube start

# enable ingress addon
minikube addons enable ingress

# add admin role to default user such that pod can acces minikube api
kubectl create clusterrolebinding add-on-cluster-admin2 --clusterrole=cluster-admin --serviceaccount=default:default

# ./deploy-charts-minikube.sh

# ./build_and_push_all.sh

kubectl apply -f ./k8s/coordinator-app.yaml
kubectl apply -f ./k8s/ingress-service.yaml
kubectl apply -f ./k8s/order-app.yaml
kubectl apply -f ./k8s/order-sharding-service.yaml
kubectl apply -f ./k8s/payment-app.yaml
kubectl apply -f ./k8s/stock_updater.yaml
kubectl apply -f ./k8s/stock-app.yaml

#start tunnel
minikube tunnel