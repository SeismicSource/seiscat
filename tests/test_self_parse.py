# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for `seiscat self` argument parsing."""

import unittest
from unittest.mock import patch

from seiscat.config.parse_arguments import parse_arguments


class TestSelfParse(unittest.TestCase):
    """Test `seiscat self` parser tree."""

    @patch('sys.argv', ['seiscat', 'self', 'status'])
    def test_self_status_parse(self):
        args = parse_arguments()
        self.assertEqual(args.action, 'self')
        self.assertEqual(args.self_action, 'status')

    @patch('sys.argv', ['seiscat', 'self', 'update'])
    def test_self_update_parse(self):
        args = parse_arguments()
        self.assertEqual(args.action, 'self')
        self.assertEqual(args.self_action, 'update')
        self.assertFalse(args.git)

    @patch('sys.argv', ['seiscat', 'self', 'update', '--git'])
    def test_self_update_git_parse(self):
        args = parse_arguments()
        self.assertEqual(args.action, 'self')
        self.assertEqual(args.self_action, 'update')
        self.assertTrue(args.git)

    @patch('sys.argv', ['seiscat', 'self', 'completion', 'install'])
    def test_self_completion_install_parse(self):
        args = parse_arguments()
        self.assertEqual(args.action, 'self')
        self.assertEqual(args.self_action, 'completion')
        self.assertEqual(args.self_completion_action, 'install')

    @patch('sys.argv', ['seiscat', 'self'])
    def test_self_without_subcommand_shows_help(self):
        with self.assertRaises(SystemExit) as cm:
            parse_arguments()
        self.assertEqual(cm.exception.code, 0)

    @patch('sys.argv', ['seiscat', 'self', 'completion'])
    def test_self_completion_without_subcommand_shows_help(self):
        with self.assertRaises(SystemExit) as cm:
            parse_arguments()
        self.assertEqual(cm.exception.code, 0)

    @patch('sys.argv', ['seiscat', 'logo'])
    def test_top_level_logo_removed(self):
        with self.assertRaises(SystemExit):
            parse_arguments()
