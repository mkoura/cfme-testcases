# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Filter out testcases that are already in Polarion.
"""

from __future__ import unicode_literals, absolute_import

import os
import logging

from xml.etree import ElementTree

from cfme_testcases.exceptions import TestcasesException
from cfme_testcases.msglog import parse


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def get_testcases(testcase_file, missing):
    """Gets testcases missing in Polarion."""
    try:
        xml_tree = ElementTree.parse(os.path.expanduser(testcase_file))
        xml_root = xml_tree.getroot()
    # pylint: disable=broad-except
    except Exception as err:
        raise TestcasesException("Failed to parse XML file '{}': {}".format(testcase_file, err))

    if xml_root.tag == 'testcases':
        testcase_parent = xml_root
        testcase_instances = testcase_parent.findall('testcase')
        attr = 'id'
    elif xml_root.tag == 'testsuites':
        testsuite = xml_root.find('testsuite')
        testcase_parent = testsuite
        testcase_instances = testcase_parent.findall('testcase')
        attr = 'name'
    else:
        raise TestcasesException(
            "XML file '{}' is not in expected format: {}".format(testcase_file, err))

    for testcase in testcase_instances:
        tc_id = testcase.get(attr)
        if tc_id and tc_id not in missing:
            testcase_parent.remove(testcase)

    if xml_root.tag == 'testsuites':
        testcase_parent.set('tests', str(len(testcase_parent.findall('testcase'))))
        testcase_parent.attrib.pop('errors', None)
        testcase_parent.attrib.pop('failures', None)
        testcase_parent.attrib.pop('skipped', None)

    return ElementTree.tostring(xml_root, encoding='utf8')


def get_filtered_xmls(testcases_xml, testsuites_xml, msgbus_log):
    """Returns modified XMLs with testcases and testsuites."""
    import_outcome = parse(os.path.expanduser(msgbus_log))
    missing = set(import_outcome['not_found'])
    if not missing:
        logger.info(
            "Nothing to do, no missing testcases found in the logfile '{}'".format(msgbus_log))
        return None, None

    testcases = get_testcases(os.path.expanduser(testcases_xml), missing)
    testsuites = get_testcases(os.path.expanduser(testsuites_xml), missing)

    return (testcases, testsuites)
