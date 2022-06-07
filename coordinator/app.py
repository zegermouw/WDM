from flask import Flask, request
from coordinatorutils import prepare_stock, commit_stock, rollback_stock, prepare_pay, commit_pay, rollback_pay

app = Flask("coordinator-service")


@app.post('/pay/<user_id>/<order_id>/<price>')
def pay_order(user_id, order_id, price):
    # locking(user_id, item_id)

    item_ids = request.json

    prepare1 = prepare_stock(item_ids)
    prepare2 = prepare_pay(user_id, order_id, price)

    # confirmation from order and payment
    if prepare1 == 200 and prepare2 == 200:
        # send commit to order and payment
        commit1 = commit_stock(item_ids)
        commit2 = commit_pay(user_id, order_id, price)
        if commit1 == 200 and commit2 == 200:
            return 'order is payed', 200
        else:
            # TODO: Test if this works correctly
            if commit2 == 200 and commit1 != 200:
                return rollback_pay(user_id, order_id, price)
            elif commit1 == 200 and commit2 != 200:
                return rollback_stock(item_ids)
            else:
                rollback_stock(item_ids)
                rollback_pay(user_id, order_id, price)
                return 'Rolled back both stock and pay', 200

    else:
        # unlock
        locking(user_id, order_id)


def locking(user_id, order_id):
    # do lock logic
    print('')
