# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Create new testrun and upload missing testcases using Polarion Importers.
"""

from __future__ import unicode_literals, absolute_import

import argparse
import datetime
import io
import logging
import os
import random
import string
import threading

from dump2polarion import configuration, submit

from cfme_testcases import filters, gen_xmls, utils
from cfme_testcases.exceptions import NothingToDoException, TestcasesException


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
    parser.add_argument('--no-testrun-update', action='store_true',
                        help="Don't add new testcases to testrun")
    parser.add_argument('--no-testcases-update', action='store_true',
                        help="Don't update existing testcases")
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
    parser.add_argument('--job-log',
                        help="Path to an existing job log file")
    parser.add_argument('--no-verify', action='store_true',
                        help="Don't verify submission success")
    parser.add_argument('--verify-timeout', type=int, default=300, metavar='SEC',
                        help="How long to wait (in seconds) for verification of submission success"
                             " (default: %(default)s)")
    parser.add_argument('--log-level',
                        help="Set logging to specified level")
    return parser.parse_args(args)


def get_submit_args(args):
    """Gets arguments for the ``submit_and_verify`` method."""
    submit_args = dict(
        testrun_id=args.testrun_id,
        user=args.user,
        password=args.password,
        no_verify=args.no_verify,
        verify_timeout=args.verify_timeout,
    )
    return {k: v for k, v in submit_args.items() if v is not None}


def init_log(log_level):
    """Initializes logging."""
    log_level = log_level or 'INFO'
    logging.basicConfig(
        format='%(name)s:%(levelname)s:%(message)s',
        level=getattr(logging, log_level.upper(), logging.INFO))


def write_xml(xml_root, filename):
    """Outputs the XML content into a file."""
    if xml_root is None:
        raise TestcasesException("No data to write.")

    xml_str = utils.etree_to_string(xml_root)
    with io.open(filename, 'w', encoding='utf-8') as xml_file:
        xml_file.write(utils.get_unicode_str(xml_str))
    logger.info("Data written to '{}'".format(filename))


def gen_pytest_xmls(args):
    """Generates the XML files when they were not specified on command line."""
    if args.testcases and args.testsuites:
        return

    if not args.testrun_id:
        raise TestcasesException("The testrun id was not specified")
    gen_xmls.run_pytest(args.testrun_id)


def _get_filename_str(args):
    return '{}-{:%Y%m%d%H%M%S}'.format(
        args.testrun_id or
        ''.join(random.sample(string.ascii_lowercase, 5)), datetime.datetime.now())


def _get_import_file_name(args, file_name, path, key):
    return os.path.join(
        path,
        'import-{0}-{1}-{2}'.format(_get_filename_str(args), key, file_name))


def get_init_logname(args):
    """Returns filename of the message bus log file."""
    if args.job_log:
        job_log = args.job_log
    else:
        job_log = 'init-job-{}.log'.format(_get_filename_str(args))
        job_log = os.path.join(args.output_dir or '', job_log)
    return job_log


def initial_submit(args, submit_args, config, log):
    """Submits XML to Polarion and saves the log file returned by the message bus."""
    if os.path.isfile(log) and not args.testrun_init:
        # log file already exists, no need to generate one
        return
    elif args.no_submit:
        raise NothingToDoException(
            "Instructed not to submit and as the message bus log is missing, "
            "there's nothing more to do")

    if args.testrun_init:
        # we want to init new test run
        fname = _TEST_RUN_XML
        xml_root = utils.get_xml_root(fname)
    else:
        # we want to just get the log file without changing anything
        fname = _TEST_CASE_XML
        xml_root = utils.get_xml_root(fname)
        utils.set_dry_run(xml_root)
        utils.set_lookup_method(xml_root, 'name')

    utils.remove_response_property(xml_root)

    if args.output_dir:
        path, name = os.path.split(fname)
        init_file = _get_import_file_name(args, name, args.output_dir or path, 'init')
        write_xml(xml_root, init_file)

    if not submit.submit_and_verify(
            xml_root=xml_root,
            config=config,
            log_file=log,
            **submit_args):
        raise TestcasesException("Failed to do the initial submit")


def save_filtered_xmls(args, testcases, testsuites, filtered_xmls):
    """Saves the generated XML files if instructed to do so."""
    if not (args.no_submit or args.output_dir):
        return

    if filtered_xmls.missing_testcases is not None:
        path, name = os.path.split(testcases)
        filter_testcases_file = _get_import_file_name(
            args, name, args.output_dir or path, 'missing')
        write_xml(filtered_xmls.missing_testcases, filter_testcases_file)

        path, name = os.path.split(testsuites)
        filter_testsuites_file = _get_import_file_name(
            args, name, args.output_dir or path, 'missing')
        write_xml(filtered_xmls.missing_testsuites, filter_testsuites_file)

    if filtered_xmls.updated_testcases is not None:
        path, name = os.path.split(testcases)
        filter_testcases_file = _get_import_file_name(
            args, name, args.output_dir or path, 'update')
        write_xml(filtered_xmls.updated_testcases, filter_testcases_file)


def submit_filtered_xmls(args, submit_args, config, filtered_xmls):
    """Submits filtered XMLs to Polarion Importers."""
    if args.no_submit:
        return

    def _get_job_log(prefix):
        job_log = None
        if args.output_dir:
            job_log = 'job-{}-{}.log'.format(prefix, _get_filename_str(args))
            job_log = os.path.join(args.output_dir, job_log)
        return job_log

    succeeded = []
    failed = []

    def _append_msg(retval, msg):
        if retval:
            succeeded.append(msg)
        else:
            failed.append(msg)

    # update existing testcases
    output = []
    updating_testcases_t = None
    if not args.no_testcases_update and filtered_xmls.updated_testcases is not None:
        job_log = _get_job_log('update')
        all_submit_args = dict(
            xml_root=filtered_xmls.updated_testcases,
            config=config,
            log_file=job_log,
            **submit_args)

        # run it in separate thread so we can continue without waiting
        # for the submit to finish
        def _run_submit(results, args_dict):
            retval = submit.submit_and_verify(**args_dict)
            results.append(retval)

        updating_testcases_t = threading.Thread(
            target=_run_submit, args=(output, all_submit_args,))
        updating_testcases_t.start()

    # create missing testcases in Polarion
    missing_testcases_submitted = False
    if filtered_xmls.missing_testcases is not None:
        job_log = _get_job_log('testcases')
        retval = submit.submit_and_verify(
            xml_root=filtered_xmls.missing_testcases,
            config=config,
            log_file=job_log,
            **submit_args
        )
        missing_testcases_submitted = retval
        _append_msg(retval, 'add missing testcases')

    # add missing testcases to testrun
    if (missing_testcases_submitted and
            not args.no_testrun_update and
            filtered_xmls.missing_testsuites is not None):
        job_log = _get_job_log('testrun')
        retval = submit.submit_and_verify(
            xml_root=filtered_xmls.missing_testsuites,
            config=config,
            log_file=job_log,
            **submit_args
        )
        _append_msg(retval, 'update testrun')

    if updating_testcases_t:
        updating_testcases_t.join()
        _append_msg(output.pop(), 'update existing testcases')

    if succeeded and failed:
        logger.info("SUCCEEDED to {}".format(', '.join(succeeded)))
    if failed:
        raise TestcasesException("FAILED to {}".format(', '.join(failed)))

    logger.info("DONE - RECORDS SUCCESSFULLY UPDATED!")


def main(args=None):
    """Main function for cli."""
    args = get_args(args)
    submit_args = get_submit_args(args)

    init_log(args.log_level)

    dump2polarion_config = configuration.get_config(
        args.dump2polarion_config) if args.dump2polarion_config else None

    testcases = args.testcases or _TEST_CASE_XML
    testsuites = args.testsuites or _TEST_RUN_XML

    try:
        gen_pytest_xmls(args)
        init_logname = get_init_logname(args)
        initial_submit(args, submit_args, dump2polarion_config, init_logname)
        filtered_xmls = filters.get_filtered_xmls(testcases, testsuites, init_logname)
        save_filtered_xmls(args, testcases, testsuites, filtered_xmls)
        submit_filtered_xmls(args, submit_args, dump2polarion_config, filtered_xmls)
    except NothingToDoException as einfo:
        logger.info(einfo)
        return 0
    except TestcasesException as err:
        logger.fatal(err)
        return 1
    return 0
