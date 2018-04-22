#!/usr/bin/python3
# -*- coding: utf-8 -*-

import unittest
import sys
from src.tu_recibot import login



class TestStringMethods(unittest.TestCase):

    def test_upper(self):
        cookies = login("34928764", "tataglia23", "swissmedical")
        self.assertEqual(cookies is not None)


if __name__ == '__main__':
    unittest.main()