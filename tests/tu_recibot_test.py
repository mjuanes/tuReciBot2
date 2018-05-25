#!/usr/bin/python3
# -*- coding: utf-8 -*-

import unittest
import sys
from src.tu_recibot import login
from src.tu_recibot import get_documents
from src.tu_recibot import get_categories2

dni = "xxxxxxx"
password = "xxxxxx"
site = "xxxxxxx"


class TestMethods(unittest.TestCase):

    def setUp(self):
        self.cookies = login(dni, password, site)

    def test_login(self):
        cookies = login(dni, password, site)
        self.assertTrue(len(cookies) > 0, "Error loggin in.")
        self.cookies = cookies

    def test_get_categories(self):
        categories = get_categories2(self.cookies, site)
        self.assertTrue(len(categories) > 0, "Error getting categories.")

    def test_get_documents(self):
        documents = get_documents(self.cookies, site)
        self.assertTrue(len(documents) > 0, "Error getting documents.")


if __name__ == '__main__':
    unittest.main()
