import unittest
import utils as tu
import grequests

class TestPaxos(unittest.TestCase):

    def test_simple_update(self):
        # Create user.
        item: dict = tu.create_user_service0()
        self.assertTrue('user_id' in item)

        # Check if user is also created at other service.
        item1: dict = tu.find_user_service1(item['user_id'])
        self.assertTrue('user_id' in item1)

        # Check prepare endpoint
        status: int = tu.test_prepare_endpoint(1, {'user_id': '12345', 'credit': 1})
        self.assertEqual(status, 200)

        # Update users credit.
        amount = 500
        status: int = tu.add_credit_to_user0(item['user_id'], amount)
        self.assertEqual(status, 200)
        
        # Find users at both services and check if credit is same
        user_1 = tu.find_user_service1(item['user_id'])
        user_0 = tu.find_user_service0(item['user_id'])
        self.assertEqual(user_1['credit'],  amount)
        self.assertEqual(user_0['credit'], amount)

    def test_two_simultanious_updates(self):
        # Create user.
        item: dict = tu.create_user_service0()
        self.assertTrue('user_id' in item)

        # Try updating two replicas at the same time       
        async_list = [
                tu.async_add_credit_to_user(item['user_id'], 500, 0),
                tu.async_add_credit_to_user(item['user_id'], 400, 1)
                ]
        r = grequests.map(async_list, size=len(async_list))
        self.assertEquals(r[1].status_code, 400)

if __name__ == '__main__':
    unittest.main()
