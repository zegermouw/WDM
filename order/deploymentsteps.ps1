
minikube start
# enable ingress addon
minikube addons enable ingress
#start tunnel
minikube tunnel
# add admin role to default user such that pod can acces minikube api
kubectl create clusterrolebinding add-on-cluster-admin2 --clusterrole=cluster-admin --serviceaccount=default:default