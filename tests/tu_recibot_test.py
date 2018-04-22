#!/usr/bin/python3
# -*- coding: utf-8 -*-

import unittest
import sys
from src.tu_recibot import login
from src.tu_recibot import get_documents
from src.tu_recibot import get_categories

dni = "xxxxxx"
password = "xxxxxx"
site = "xxxxxxx"


class TestStringMethods(unittest.TestCase):

    def setUp(self):
        self.cookies = login(dni, password, site)

    def test_login(self):
        cookies = login(dni, password, site)
        self.assertTrue(len(cookies) > 0, "Error while login")

    def test_get_documents(self):
        categories = get_categories(self.cookies, site)
        self.assertTrue(len(categories) > 1, "Error while login")


if __name__ == '__main__':
    unittest.main()