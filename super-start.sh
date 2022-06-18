if [minikube status ]
minikube start

./deploy-charts-minikube.sh

cd ./k8s
kubectl apply -f .