# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Filter missing testcases and testcases for update.
"""

from __future__ import absolute_import, unicode_literals

import logging
import os

from collections import namedtuple

from cfme_testcases import parselog, utils
from cfme_testcases.exceptions import TestcasesException


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)

FilteredXMLs = namedtuple('FilteredXMLs', 'missing_testcases missing_testsuites updated_testcases')


def get_missing_testcases(testcase_file, missing):
    """Gets testcases missing in Polarion."""
    if not missing:
        return

    xml_root = utils.get_xml_root(testcase_file)

    if xml_root.tag != 'testcases':
        raise TestcasesException(
            "XML file '{}' is not in expected format".format(testcase_file))

    utils.remove_response_property(xml_root)

    testcase_instances = xml_root.findall('testcase')
    attr = 'id'

    for testcase in testcase_instances:
        tc_id = testcase.get(attr)
        if tc_id and tc_id not in missing:
            xml_root.remove(testcase)

    return xml_root


def get_missing_testsuites(testsuite_file, missing):
    """Gets testcases missing in testrun."""
    if not missing:
        return

    xml_root = utils.get_xml_root(testsuite_file)

    if xml_root.tag != 'testsuites':
        raise TestcasesException(
            "XML file '{}' is not in expected format".format(testsuite_file))

    utils.remove_response_property(xml_root)

    testsuite = xml_root.find('testsuite')
    testcase_parent = testsuite
    testcase_instances = testcase_parent.findall('testcase')
    attr = 'name'

    for testcase in testcase_instances:
        tc_id = testcase.get(attr)
        if tc_id and tc_id not in missing:
            testcase_parent.remove(testcase)

    testcase_parent.set('tests', str(len(testcase_parent.findall('testcase'))))
    testcase_parent.attrib.pop('errors', None)
    testcase_parent.attrib.pop('failures', None)
    testcase_parent.attrib.pop('skipped', None)

    return xml_root


def get_updated_testcases(testcase_file, missing):
    """Gets testcases that will be updated in Polarion."""
    if missing is None:
        missing = []

    xml_root = utils.get_xml_root(testcase_file)

    if xml_root.tag != 'testcases':
        raise TestcasesException(
            "XML file '{}' is not in expected format".format(testcase_file))

    utils.remove_response_property(xml_root)
    utils.set_lookup_method(xml_root, 'name')

    testcase_instances = xml_root.findall('testcase')
    # we lookup using "title" here, but it's value is the same as the value of "id"
    attr = 'id'

    for testcase in testcase_instances:
        tc_id = testcase.get(attr)
        if tc_id is not None and tc_id in missing:
            xml_root.remove(testcase)
            continue
        cfields_parent = testcase.find('custom-fields')
        cfields_instances = cfields_parent.findall('custom-field')
        for field in cfields_instances:
            field_id = field.get('id')
            if field_id not in ('automation_script',):
                cfields_parent.remove(field)

    return xml_root


def get_filtered_xmls(testcases_xml, testsuites_xml, job_log):
    """Returns modified XMLs with testcases and testsuites."""
    import_outcome = parselog.parse(os.path.expanduser(job_log))
    missing = set(import_outcome['not_found'])

    missing_testcases = get_missing_testcases(os.path.expanduser(testcases_xml), missing)
    missing_testsuites = get_missing_testsuites(os.path.expanduser(testsuites_xml), missing)
    updated_testcases = get_updated_testcases(os.path.expanduser(testcases_xml), missing)

    return FilteredXMLs(missing_testcases, missing_testsuites, updated_testcases)
