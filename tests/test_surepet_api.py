import os
import tempfile
import unittest

from sure_petcare.sure_petcare_api import SurePetApi


class SurePetApiTestCase(unittest.TestCase):
    def setup_method(self, method):
        self.cache_file = tempfile.NamedTemporaryFile()

    def teardown_method(self, method):
        os.remove(self.cache_file.name)

    def test_init(self):
        api = SurePetApi(
            email_address="test@test.com",
            password="test",
            cache_file=self.cache_file.name,
        )
        assert api.cache_file == self.cache_file.name
        assert api._init_email == "test@test.com"
        assert api._init_pw == "test"
