import requests

user_id = requests.post("http://localhost/payment/create_user")
print(user_id.content)
