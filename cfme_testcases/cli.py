# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Create new testrun and upload missing testcases using Polarion XUnit Importer.
"""

from __future__ import unicode_literals, absolute_import

import os
import datetime
import string
import random
import argparse
import logging

from xml.etree import ElementTree

from dump2polarion.configuration import get_config
from dump2polarion.submit import submit_and_verify

from cfme_testcases.exceptions import TestcasesException
from cfme_testcases.filters import get_filtered_xmls
from cfme_testcases.gen_xmls import run_pytest


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


_TEST_RUN_XML = 'test_run_import.xml'
_TEST_CASE_XML = 'test_case_import.xml'


def get_args(args=None):
    """Get command line arguments."""
    parser = argparse.ArgumentParser(description='cfme-testcases')
    parser.add_argument('-t', '--testrun-id',
                        help="Polarion test run id")
    parser.add_argument('-o', '--output_dir',
                        help="Directory for saving generated XML files")
    parser.add_argument('-n', '--no-submit', action='store_true',
                        help="Don't submit generated XML files")
    parser.add_argument('--testrun-init', action='store_true',
                        help="Create and initialize new testrun")
    parser.add_argument('--user',
                        help="Username to use to submit to Polarion")
    parser.add_argument('--password',
                        help="Password to use to submit to Polarion")
    parser.add_argument('--testcases',
                        help="Path to XML file with testcases")
    parser.add_argument('--testsuites',
                        help="Path to xunit XML file with testsuites")
    parser.add_argument('--dump2polarion-config',
                        help="Path to dump2polarion config YAML")
    parser.add_argument('--msgbus-log',
                        help="Path to an existing message bus log file")
    parser.add_argument('--no-verify', action='store_true',
                        help="Don't verify submission success")
    parser.add_argument('--verify-timeout', type=int, default=300, metavar='SEC',
                        help="How long to wait (in seconds) for verification of submission success"
                             " (default: %(default)s)")
    parser.add_argument('--log-level',
                        help="Set logging to specified level")
    return parser.parse_args(args)


def init_log(log_level):
    """Initializes logging."""
    log_level = log_level or 'INFO'
    logging.basicConfig(
        format='%(name)s:%(levelname)s:%(message)s',
        level=getattr(logging, log_level.upper(), logging.INFO))


def write_xml(xml, filename):
    """Outputs the XML content into a file."""
    if not xml:
        raise TestcasesException("No data to write.")

    with open(filename, 'w') as xml_file:
        xml_file.write(xml)
    logger.info("Data written to '{}'".format(filename))


def set_dry_run(xml_file):
    """Sets dry-run so testrun is not updated, only log file is produced."""
    try:
        tree = ElementTree.parse(xml_file)
        xml_root = tree.getroot()
    # pylint: disable=broad-except
    except Exception as err:
        raise TestcasesException("Failed to parse XML file: {}".format(err))

    properties = xml_root.find('properties')
    for prop in properties:
        if prop.get('name') == 'polarion-dry-run':
            prop.set('value', 'true')
            break
    else:
        ElementTree.SubElement(properties, 'property',
                               {'name': 'polarion-dry-run', 'value': 'true'})

    return ElementTree.tostring(xml_root, encoding='utf8')


# pylint: disable=too-many-locals,too-many-return-statements,too-many-branches,too-many-statements
def main(args=None):
    """Main function for cli."""
    args = get_args(args)

    def _get_filename_str():
        return '{}-{:%Y%m%d%H%M%S}'.format(
            args.testrun_id or ''.join(random.sample(string.lowercase, 5)), datetime.datetime.now())

    init_log(args.log_level)

    dump2polarion_config = get_config(
        args.dump2polarion_config) if args.dump2polarion_config else None

    # if the XML files were not specified on command line, generate them using pytest
    if not(args.testcases and args.testsuites):
        if not args.testrun_id:
            logger.fatal("The testrun id was not specified")
            return 1
        try:
            run_pytest(args.testrun_id)
        except TestcasesException as err:
            logger.fatal(err)
            return 1

    # submit testrun XML to Polarion and save the log file returned by the message bus
    if args.msgbus_log:
        # log file was passed as command line argument, no need to generate one
        msgbus_log = args.msgbus_log
    elif args.no_submit:
        logger.info(
            "Instructed not to submit testrun and as the message bus log is missing, "
            "there's nothing more to do")
        return 0
    else:
        nargs = {}
        nargs.update(vars(args))
        msgbus_log = 'msgbus-testrun-init-{}.log'.format(_get_filename_str())
        msgbus_log = os.path.join(args.output_dir or '', msgbus_log)
        nargs['msgbus_log'] = msgbus_log
        if not args.testrun_init:
            xml_input = set_dry_run(_TEST_RUN_XML)
            nargs['xml_str'] = xml_input
        else:
            nargs['xml_file'] = _TEST_RUN_XML
        if not submit_and_verify(config=dump2polarion_config, **nargs):
            logger.fatal("Failed to submit testrun")
            return 1

    # filter testcases based on message bus log
    testcases = args.testcases or _TEST_CASE_XML
    testsuites = args.testsuites or _TEST_RUN_XML
    try:
        filtered_testcases, filtered_testsuites = get_filtered_xmls(
            testcases, testsuites, msgbus_log)
    except TestcasesException as err:
        logger.fatal(err)
        return 1

    # save the generated XML files if instructed to do so
    if (args.no_submit or args.output_dir) and filtered_testcases:

        def _get_import_file_name(file_name, path):
            return os.path.join(
                path,
                'import-{}-{}'.format(_get_filename_str(), file_name))

        path, name = os.path.split(testcases)
        filter_testcases_file = _get_import_file_name(name, args.output_dir or path)
        write_xml(filtered_testcases, filter_testcases_file)

        path, name = os.path.split(testsuites)
        filter_testsuites_file = _get_import_file_name(name, args.output_dir or path)
        write_xml(filtered_testsuites, filter_testsuites_file)

    # create missing testcases in Polarion and add them to testrun
    if not args.no_submit and filtered_testcases:
        nargs = {}
        nargs.update(vars(args))
        msgbus_log = None
        if args.output_dir:
            msgbus_log = 'msgbus-testcases-{}.log'.format(_get_filename_str())
            msgbus_log = os.path.join(args.output_dir, msgbus_log)
        nargs['msgbus_log'] = msgbus_log
        if not submit_and_verify(filtered_testcases, config=dump2polarion_config, **nargs):
            logger.fatal("Failed to submit new testcases")
            return 1

        msgbus_log = None
        if args.output_dir:
            msgbus_log = 'msgbus-testrun-{}.log'.format(_get_filename_str())
            msgbus_log = os.path.join(args.output_dir, msgbus_log)
        nargs['msgbus_log'] = msgbus_log
        if not submit_and_verify(filtered_testsuites, config=dump2polarion_config, **nargs):
            logger.fatal(
                "Failed to submit new testcases into testrun {}".format(args.testrun_id or ''))
            return 1

        logger.info("Done - testrun and missing testcases successfully submitted!")
