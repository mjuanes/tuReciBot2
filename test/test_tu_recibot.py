#!/usr/bin/python3
# -*- coding: utf-8 -*-

import unittest

from tu_recibot import get_categories
from tu_recibot import get_documents
from tu_recibot import get_companies
from tu_recibot import login

from os import environ

# Complete me
dni = environ['DNI']
password = environ['PASSWORD']
site = environ['SITE']


class TestMethods(unittest.TestCase):

    def setUp(self):
        self.cookies = login(dni, password, site)

    def test_login(self):
        self.assertTrue(len(self.cookies) > 0, "Error in logging.")

    def test_get_categories(self):
        categories = get_categories(self.cookies, site)
        self.assertTrue(len(categories) > 0, "Error getting categories.")

    def test_get_documents(self):
        documents = get_documents(self.cookies, site)
        self.assertTrue(len(documents) > 0, "Error getting documents.")

    def test_get_companies(self):
        companies = get_companies(self.cookies, site)
        self.assertTrue(len(companies) > 0, "Error getting documents.")


if __name__ == '__main__':
    unittest.main()
