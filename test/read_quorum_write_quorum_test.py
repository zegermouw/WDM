import unittest
import utils as tu


class TestReadQuorumWriteQuorum(unittest.TestCase):

    def test_add_stock(self):
        item: dict = tu.create_item(5)
        self.assertTrue('item_id' in item)

        item_id: str = item['item_id']

        item: dict = tu.find_item(item_id)
        self.assertEqual(item['price'], 5)
        
        add_stock_response = tu.add_stock(item_id, 50)
        self.assertTrue(200 <= int(add_stock_response) < 300)


if __name__ == '__main__':
    unittest.main()
