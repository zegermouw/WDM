import unittest
from paxos import Paxos
import logging
import sys
replicas = []
db = None
paxos = Paxos(replicas, db)


class PaxosUnitTest(unittest.TestCase):

    def test_acceptor_prepare(self):
        res, status = paxos.acceptor_prepare(1, {'user_id': "1234str", "credit":1})
        self.assertEqual(status, 200)

    def test_proposer_accept(self):
        pass 

if __name__=='__main__':
    logging.basicConfig( stream=sys.stderr )
    logging.getLogger( "SomeTest.testSomething" ).setLevel( logging.DEBUG )
    unittest.main()
