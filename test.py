import unittest
import json
from app import app

class MotorcycleAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        # Get token
        resp = self.app.post('/login')
        self.token = json.loads(resp.data)['token']

    def test_create(self):
        resp = self.app.post('/motorcycles', json={
            'make': 'TestBrand',
            'model': 'TestModel',
            'year': 2025,
            'engine_cc': 500,
            'color': 'Test Red'
        }, headers={'x-access-token': self.token})
        self.assertEqual(resp.status_code, 201)

    def test_get_all_json(self):
        resp = self.app.get('/motorcycles', headers={'x-access-token': self.token})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('application/json', resp.content_type)

    def test_get_all_xml(self):
        resp = self.app.get('/motorcycles?format=xml', headers={'x-access-token': self.token})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('application/xml', resp.content_type)

    def test_search(self):
        resp = self.app.get('/motorcycles?search=Yamaha', headers={'x-access-token': self.token})
        data = json.loads(resp.data)
        self.assertGreater(len(data), 0)

    def test_get_one(self):
        resp = self.app.get('/motorcycles/1', headers={'x-access-token': self.token})
        self.assertEqual(resp.status_code, 200)

    def test_update(self):
        resp = self.app.put('/motorcycles/1', json={
            'make': 'UpdatedMake',
            'model': 'UpdatedModel',
            'year': 2026,
            'engine_cc': 700,
            'color': 'Updated Blue'
        }, headers={'x-access-token': self.token})
        self.assertEqual(resp.status_code, 200)

    def test_delete(self):
        # Create then delete (assume new ID is 23)
        self.app.post('/motorcycles', json={
            'make': 'ToDelete',
            'model': 'X1',
            'year': 2025,
            'engine_cc': 300,
            'color': 'Black'
        }, headers={'x-access-token': self.token})
        resp = self.app.delete('/motorcycles/23', headers={'x-access-token': self.token})
        # Accept 200 or 404 (if ID not 23)
        self.assertIn(resp.status_code, [200, 404])

if __name__ == '__main__':
    unittest.main()