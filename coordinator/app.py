from flask import Flask
from coordinatorutils import prepare_checkout, commit_checkout, prepare_pay, commit_pay, rollback_checkout, rollback_pay

app = Flask("coordinator-service")


@app.post('/pay/<order_id>')
def pay_order(user_id, order_id, amount):
    # send prepare to order --> lock the order, cannot be changed anymore or deleted
    prepare1 = prepare_checkout(order_id)
    # send prepare to payment --> lock credits, user cannot be credited or debited
    prepare2 = prepare_pay(user_id, order_id, amount)

    # confirmation from order and payment
    if prepare1 == 200 and prepare2 == 200:
        # send commit to order and payment
        commit1 = commit_checkout(order_id)
        commit2 = commit_pay(user_id, order_id, amount)
        if commit1 == 200 and commit2 == 200:
            return 'order is payed', 200
        else:
            # what happens if one message commits and the other not?
            print('what do we do here?')

    # confirmation failed
    else:
        # send rollback message to payment and order
        rollback1 = rollback_checkout(order_id)
        rollback2 = rollback_pay(user_id, order_id, amount)
        if rollback1 == 200 and rollback2 == 200:
            return 'order failed and rolled back to previous state', 200
        else:
            # what happens when one rollback succeeds but the other not?
            print('what do we do here?')



