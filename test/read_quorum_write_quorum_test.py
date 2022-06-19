import unittest
import utils as tu


class TestReadQuorumWriteQuorum(unittest.TestCase):

    def test_add_stock(self):
        item: dict = tu.create_item(5)
        self.assertTrue('item_id' in item)

        item_id: str = item['item_id']

        item: dict = tu.find_item(item_id)
        self.assertEqual(item['price'], 5)
        
        # add stock
        add_stock_response = tu.add_stock(item_id, 50)
        self.assertTrue(200 <= int(add_stock_response) < 300)

        # remove stock
        #remove_stock_response = tu.subtract_stock(item_id, 30)

        for i in range(3):
            item: dict = tu.find_item(item_id)
            self.assertTrue('item_id' in item)
            self.assertEqual(item['stock'], 50)


if __name__ == '__main__':
    unittest.main()
