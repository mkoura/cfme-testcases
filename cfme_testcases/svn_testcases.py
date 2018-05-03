# -*- coding: utf-8 -*-
# pylint: disable=too-few-public-methods
"""
Testcases data from Polarion SVN repo.
"""

from __future__ import absolute_import, unicode_literals

import logging
import os

from collections import defaultdict

from lxml import etree


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


class InvalidObject(object):
    """Item not present or it's not testcase."""
    pass


class WorkItemCache(object):
    """Cache of Polarion workitems."""
    def __init__(self, repo_dir):
        self.repo_dir = repo_dir
        self.test_case_dir = os.path.join(self.repo_dir, 'tracker/workitems/')
        self._cache = defaultdict(dict)

    @staticmethod
    def get_path(num):
        """Gets a path from the workitem number

        For example: 31942 will return 30000-39999/31000-31999/31900-31999
        """
        num = int(num)
        dig_len = len(str(num))
        paths = []
        for i in range(dig_len - 2):
            divisor = 10 ** (dig_len - i - 1)
            paths.append(
                '{}-{}'.format((num / divisor) * divisor, (((num / divisor) + 1) * divisor) - 1))
        return '/'.join(paths)

    def get_tree(self, work_item_id):
        """Gets XML tree of the workitem."""
        try:
            __, tcid = work_item_id.split('-')
        except ValueError:
            logger.warning('Couldn\'t load workitem %s, bad format', work_item_id)
            self._cache[work_item_id] = InvalidObject()
            return None

        path = os.path.join(
            self.test_case_dir, self.get_path(tcid), work_item_id, 'workitem.xml')
        try:
            tree = etree.parse(path)
        # pylint: disable=broad-except
        except Exception:
            logger.warning('Couldn\'t load workitem %s', work_item_id)
            self._cache[work_item_id] = InvalidObject()
            return None
        return tree

    def __getitem__(self, work_item_id):
        if work_item_id in self._cache:
            return self._cache[work_item_id]
        elif isinstance(self._cache[work_item_id], InvalidObject):
            return None

        tree = self.get_tree(work_item_id)
        if not tree:
            return

        for item in tree.xpath('/work-item/field'):
            self._cache[work_item_id][item.attrib['id']] = item.text

        if self._cache[work_item_id]['type'] != 'testcase':
            self._cache[work_item_id] = InvalidObject()
            return None

        if 'assignee' not in self._cache[work_item_id]:
            self._cache[work_item_id]['assignee'] = ''
        if 'title' not in self._cache[work_item_id]:
            logger.warning('work item %s has no title', work_item_id)

        return self._cache[work_item_id]


class PolarionTestcases(object):
    """Loads and access Polarion testcases."""

    def __init__(self, repo_dir):
        self.repo_dir = os.path.expanduser(repo_dir)
        self.wi_cache = WorkItemCache(self.repo_dir)
        self.available_testcases = {}

    def load_active_testcases(self):
        """Creates dict of all active testcase's names and ids."""
        cases = {}
        for item in os.walk(self.wi_cache.test_case_dir):
            if 'workitem.xml' not in item[2]:
                continue
            case_id = os.path.split(item[0])[-1]
            if not (case_id and '*' not in case_id):
                continue
            item_cache = self.wi_cache[case_id]
            if not item_cache:
                continue
            case_status = item_cache.get('status')
            if not case_status or case_status == 'inactive':
                continue
            case_title = item_cache.get('title')
            if not case_title:
                continue
            cases[case_title] = case_id

        self.available_testcases = cases

    def get_by_name(self, testcase_name):
        """Gets testcase by it's name."""
        testcase_id = self.available_testcases[testcase_name]
        return self.wi_cache[testcase_id]

    def get_by_id(self, testcase_id):
        """Gets testcase by it's id."""
        return self.wi_cache[testcase_id]

    def __iter__(self):
        return iter(self.available_testcases)

    def __len__(self):
        return len(self.available_testcases)

    def __contains__(self, item):
        return item in self.available_testcases

    def __repr__(self):
        return '<Testcases {}>'.format(self.available_testcases)


def get_missing(repo_dir, testcase_names):
    """Gets set of testcases missing in Polarion."""
    polarion_testcases = PolarionTestcases(repo_dir)
    polarion_testcases.load_active_testcases()
    missing = set(testcase_names) - set(polarion_testcases)
    return missing
