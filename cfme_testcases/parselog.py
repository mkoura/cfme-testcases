# -*- coding: utf-8 -*-
"""
Parse log file produced by Polarion Importers.
"""

from __future__ import absolute_import, unicode_literals

import os
import re

from cfme_testcases.exceptions import TestcasesException


_WORK_ITEM_SEARCH = re.compile(r"Work item: '(test_[^']+|[A-Z][^']+)' \(([^)]+)\)$")
_WARN_ITEM_SEARCH = re.compile(r" '(test_[^']+|[A-Z][^']+)'\.$")

_TEST_CASE_SEARCH = re.compile(r" test case '(test_[^']+|[A-Z][^']+)' \(([^)/]+)")
_TEST_CASE_WARN_SEARCH = _WARN_ITEM_SEARCH


def get_work_item(line):
    """Gets work item name and id."""
    res = _WORK_ITEM_SEARCH.search(line)
    try:
        return (res.group(1), res.group(2))
    except (AttributeError, IndexError):
        return


def get_warn_item(line):
    """Gets work item name of item that was not successfully imported."""
    res = _WARN_ITEM_SEARCH.search(line)
    try:
        return res.group(1)
    except (AttributeError, IndexError):
        return


def get_test_case(line):
    """Gets test case name and id."""
    res = _TEST_CASE_SEARCH.search(line)
    try:
        return (res.group(1), res.group(2))
    except (AttributeError, IndexError):
        return


def get_test_case_warn(line):
    """Gets name of test case that was not successfully imported."""
    res = _TEST_CASE_WARN_SEARCH.search(line)
    try:
        return res.group(1)
    except (AttributeError, IndexError):
        return


def parse_xunit(log_file):
    """Parse log file produced by the XUnit Iporter."""
    outcome = {'results': [], 'not_unique': [], 'not_found': []}
    with open(os.path.expanduser(log_file)) as input_file:
        for line in input_file:
            line = line.strip()
            if 'Work item: ' in line:
                work_item = get_work_item(line)
                if work_item:
                    outcome['results'].append(work_item)
            elif 'Unable to find *unique* work item' in line:
                warn_item = get_warn_item(line)
                if warn_item:
                    outcome['not_unique'].append(warn_item)
            elif 'Unable to find work item for' in line:
                warn_item = get_warn_item(line)
                if warn_item:
                    outcome['not_found'].append(warn_item)

    if not(outcome['results'] or outcome['not_unique'] or outcome['not_found']):
        raise TestcasesException("No valid data found in the log file '{}'".format(log_file))

    return outcome


def parse_test_case(log_file):
    """Parse log file produced by the Test Case Importer."""
    outcome = {'results': [], 'not_unique': [], 'not_found': []}
    with open(os.path.expanduser(log_file)) as input_file:
        for line in input_file:
            line = line.strip()
            if 'Updated test case' in line:
                updated_item = get_test_case(line)
                if updated_item:
                    outcome['results'].append(updated_item)
            elif 'Created test case' in line:
                missing_item = get_test_case(line)
                if missing_item:
                    # we don't want to store tuple as we want to
                    # search in a list and also the ID's have no
                    # meaning here
                    outcome['not_found'].append(missing_item[0])
            elif 'Found multiple work items with the title' in line:
                warn_item = get_test_case_warn(line)
                if warn_item:
                    outcome['not_unique'].append(warn_item)

    if not(outcome['results'] or outcome['not_unique'] or outcome['not_found']):
        raise TestcasesException("No valid data found in the log file '{}'".format(log_file))

    return outcome


def parse(log_file):
    """Parse log file."""
    handler = None
    with open(os.path.expanduser(log_file)) as input_file:
        for line in input_file:
            if 'Starting import of XUnit results' in line:
                handler = parse_xunit
                break
            elif 'Starting import of test cases' in line:
                handler = parse_test_case
                break
    if not handler:
        raise TestcasesException("No valid data found in the log file '{}'".format(log_file))
    return handler(log_file)
