docker build ./order -t markodorko/order
docker push markodorko/order
docker build ./stock -t markodorko/stock
docker push markodorko/stock
docker build ./stock_update_servic -t markodorko/stock-updater
docker push markodorko/stock-updater
docker build ./coordinator -t markodorko/coordinator
docker push markodorko/coordinator
docker build ./order-sharding-service -t markodorko/order-sharding
docker push markodorko/order-sharding
docker build ./payment -t markodorko/payment
docker push markodorko/payment
