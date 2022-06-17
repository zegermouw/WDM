from flask import Flask, request
from coordinatorutils import prepare_stock, commit_stock, rollback_stock, prepare_pay, commit_pay, rollback_pay, lock, \
    unlock, is_user_item_locked

app = Flask("coordinator-service")


@app.post('/pay/<user_id>/<order_id>/<price>')
def pay_order(user_id, order_id, price):
    item_ids = request.json

    # boolean value specifies if items should be locked too, can be removed if we want a less strict 2PC
    if is_user_item_locked(user_id, item_ids):
        return 'Could not satisfy request as the user or item(s) are locked', 403
    lock(user_id, item_ids, True)
    if not is_user_item_locked(user_id, item_ids):
        return 'Error during locking', 500

    prep1 = prepare_stock(item_ids)
    prep2 = prepare_pay(user_id, price)

    prepare1 = prep1.status_code
    prepare2 = prep2.status_code

    # confirmation from order and payment
    if prepare1 == 200 and prepare2 == 200:
        # send commit to order and payment
        status_stock = commit_stock(item_ids)
        status_pay = commit_pay(user_id, order_id, price)

        if status_stock == 200 and status_pay == 200:
            unlock(user_id, item_ids)
            return 'order is payed', 200
        else:
            if status_pay == 200 and status_stock != 200:
                unlock(user_id, item_ids)
                rollback_pay(user_id, price)
                return 'Stock could not be committed', 400
            elif status_stock == 200 and status_pay != 200:
                unlock(user_id, item_ids)
                rollback_stock(item_ids)
                return 'Payment was not successfully committed', 400
            else:
                rollback_stock(item_ids)
                rollback_pay(user_id, price)
                unlock(user_id, item_ids)
                return 'Error in both stock and payment commits', 400

    else:
        unlock(user_id, order_id)
        return 'Prepare phase did not succeed: ' + str(prep1.content) + str(prep2.content), 400
