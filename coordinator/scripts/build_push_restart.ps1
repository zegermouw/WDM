docker build ./coordinator -t markodorko/coordinator
docker push markodorko/coordinator
kubectl rollout restart -n default deployment coordinator-deployment