from flask import Flask, request
from coordinatorutils import prepare_stock, commit_stock, rollback_stock, prepare_pay, commit_pay, rollback_pay, lock, \
    unlock, is_user_item_locked

app = Flask("coordinator-service")


@app.post('/pay/<user_id>/<order_id>/<price>')
def pay_order(user_id, order_id, price):
    item_ids = request.json

    lock(user_id, item_ids)
    if not is_user_item_locked(user_id, item_ids):
        return 'Error during locking', 500

    prepare1 = prepare_stock(item_ids)
    prepare2 = prepare_pay(user_id, order_id, price)

    # confirmation from order and payment
    if prepare1 == 200 and prepare2 == 200:
        # send commit to order and payment
        commit1 = commit_stock(item_ids)
        commit2 = commit_pay(user_id, order_id, price)
        if commit1 == 200 and commit2 == 200:
            unlock(user_id, item_ids)
            return 'order is payed', 200
        else:
            if commit2 == 200 and commit1 != 200:
                unlock(user_id, item_ids)
                return rollback_pay(user_id, order_id, price)
            elif commit1 == 200 and commit2 != 200:
                unlock(user_id, item_ids)
                return rollback_stock(item_ids)
            else:
                rollback_stock(item_ids)
                rollback_pay(user_id, order_id, price)
                unlock(user_id, item_ids)
                return 'Rolled back both stock and pay', 200

    else:
        unlock(user_id, order_id)
