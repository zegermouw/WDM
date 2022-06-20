import requests

user_id = requests.post("http://localhost/payment/create_user").json()['user_id']

print(user_id)

ret0 = requests.post('http://localhost/payment/add_funds/' + user_id + '/2000')

print(ret0.json())

order_id = requests.post('http://localhost/orders-shard/create/' + str(user_id)).json()['order_id']

print(order_id)

item_id = requests.post('http://localhost/stock/item/create/100').json()['item_id']

print(item_id)

ret = requests.post('http://localhost/stock/add/' + str(item_id) + '/100').json()

print(str(ret))

ret2 = requests.post('http://localhost/orders-shard/addItem/' + order_id + '/' + item_id).json()

print(ret2)
ret3 = requests.post('http://localhost/orders-shard/checkout/' + order_id)

print(ret3)
print(ret3.content)

