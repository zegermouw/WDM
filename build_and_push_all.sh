docker build ./order -t zegermouw/order
docker push zegermouw/order
docker build ./stock -t zegermouw/stock
docker push zegermouw/stock
docker build ./coordinator -t zegermouw/coordinator
docker push zegermouw/coordinator
docker build ./order-sharding-service -t zegermouw/order-sharding
docker push zegermouw/order-sharding
docker build ./payment -t zegermouw/payment
docker push zegermouw/payment

