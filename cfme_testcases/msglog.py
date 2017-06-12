# -*- coding: utf-8 -*-
"""
Parse log file returned by XUnit Importer message bus.
"""

from __future__ import unicode_literals, absolute_import

import os
import re

from cfme_testcases.exceptions import TestcasesException


_WORK_ITEM_SEARCH = re.compile(r"Work item: '(test_[^']+|[A-Z][^']+)' \(([^)]+)\)$")
_WARN_ITEM_SEARCH = re.compile(r" '(test_[^']+|[A-Z][^']+)'\.$")


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


def parse(log_file):
    """Parse log file."""
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
