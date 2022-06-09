import unittest
import utils as tu
import grequests
import logging
import sys


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
        # load logger
        log = logging.getLogger('TestPaxos.test_two_simultanious_updates')
        # Create user.
        item: dict = tu.create_user_service0()
        self.assertTrue('user_id' in item)

        # Try updating two replicas at the same time       
        async_list = [
                tu.async_add_credit_to_user(item['user_id'], 500, 0),
                tu.async_add_credit_to_user(item['user_id'], 400, 1)
                ]
        r = grequests.map(async_list, size=len(async_list))
        user_0 = tu.find_user_service0(item['user_id'])
        user_1 = tu.find_user_service1(item['user_id'])
        credit0 = user_0['credit']
        credit1 = user_1['credit']
        log.debug('user_0 credit: '+str(credit0))
        log.debug('user_1 credit: '+str(credit1))
        self.assertEqual(credit0, 900)
        self.assertEqual(credit1, 900)
        self.assertEqual(r[0].status_code, 200)
        self.assertEqual(r[1].status_code, 200)

       # Try removing users mony async 
        user_id = item['user_id']
        async_list = [
               tu.async_remove_credit_from_user(user_id, 'order1', 500, 0),
               tu.async_remove_credit_from_user(user_id, 'order1', 900, 1)  
                ]
        r = grequests.map(async_list, size=len(async_list))
        log.debug('request 0 status'+str(r[0].status_code))
        log.debug('request 1 status'+str(r[1].status_code))
       
        # get users for debugging
        user_0 = tu.find_user_service0(item['user_id'])
        user_1 = tu.find_user_service1(item['user_id'])
        credit0 = user_0['credit']
        credit1 = user_1['credit']
        log.debug('user_0 credit: '+str(credit0))
        log.debug('user_1 credit: '+str(credit1))
        
        self.assertTrue(r[0].status_code==400 or r[1].status_code==400)
        self.assertTrue(r[1].status_code==200 or r[1].status_code==100)



if __name__ == '__main__':
    logging.basicConfig( stream=sys.stderr )
    logging.getLogger( 'TestPaxos.test_two_simultanious_updates' ).setLevel( logging.DEBUG )
    unittest.main()
    #testPaxos = TestPaxos()
    #testPaxos.test_two_simultanious_updates()

