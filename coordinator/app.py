from flask import Flask
from coordinatorutils import prepare_checkout, commit_checkout, prepare_pay, commit_pay, rollback_checkout, rollback_pay, write_locking_doc, write_unlocking_doc, is_user_in_doc

app = Flask("coordinator-service")


@app.get('/test')
def test():
    return 'test successful', 200

@app.post('/pay/<user_id>/<order_id>/<amount>')
def pay_order(user_id, order_id, amount):
    # send prepare to order --> lock the order, cannot be changed anymore or deleted
    print(user_id,is_user_locked(user_id))
    if is_user_locked(user_id) == False:
        lock_user_order(user_id,order_id)
        assert is_user_locked(user_id) == True
        prepare1 = prepare_checkout(order_id)
        # send prepare to payment --> lock credits, user cannot be credited or debited
        prepare2 = prepare_pay(user_id, order_id, amount)

        # confirmation from order and payment
        if prepare1 == 200 and prepare2 == 200:
            # send commit to order and payment
            commit1 = commit_checkout(order_id)
            commit2 = commit_pay(user_id, order_id, amount)
            if commit1 == 200 and commit2 == 200:
                unlock_user_order(user_id, order_id)
                assert is_user_locked(user_id) == False
                return 'order is payed', 200
            else:
                # what happens if one message commits and the other not?
                unlock_user_order(user_id, order_id)
                return 'ERROR: order not payed', 406

        # confirmation failed
        else:
            # send rollback message to payment and order
            rollback1 = rollback_checkout(order_id)
            rollback2 = rollback_pay(user_id, order_id, amount)
            if rollback1 == 200 and rollback2 == 200:
                unlock_user_order(user_id, order_id)
                return 'order failed and rolled back to previous state', 200
            else:
                # what happens when one rollback succeeds but the other not?
                unlock_user_order(user_id, order_id)
                return 'ERROR: rollback scenario', 406
    else:
        return 'ERROR: User locked', 406
    

def lock_user_order(user_id, order_id):
    write_locking_doc(user_id, order_id)

def unlock_user_order(user_id, order_id):
    write_unlocking_doc(user_id, order_id)

def is_user_locked(user_id):
    return is_user_in_doc(user_id)