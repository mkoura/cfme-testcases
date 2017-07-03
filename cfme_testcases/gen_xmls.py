# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Run pytest --collect-only and generate XMLs.
"""

from __future__ import unicode_literals, absolute_import

import os
import sys
import logging

from contextlib import contextmanager

from cfme_testcases.exceptions import TestcasesException


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


_XML_FILES = ('test_case_import.xml', 'test_run_import.xml')


def _check_environment():
    # check that launched in integration tests repo
    if not os.path.exists('cfme/tests'):
        raise TestcasesException("Not running in the integration tests repo")
    # check that running in virtualenv
    if not hasattr(sys, 'real_prefix'):
        raise TestcasesException("Not running in virtual environment")


def _cleanup():
    for fname in _XML_FILES:
        try:
            os.remove(fname)
        except OSError:
            pass


@contextmanager
def _silence_output():
    new_target = open(os.devnull, 'w')
    old_target, sys.stdout = sys.stdout, new_target
    old_log_level = logging.getLogger().getEffectiveLevel()
    logging.getLogger().setLevel(logging.ERROR)
    try:
        yield new_target
    finally:
        sys.stdout = old_target
        logging.getLogger().setLevel(old_log_level)


def run_pytest(testrun_id):
    """Runs the pytest command."""
    pytest_retval = None
    _check_environment()
    _cleanup()

    args = [
        '-qq',
        '--collect-only',
        '--long-running',
        '--use-provider', 'complete',
        '--generate-legacy-xmls',
        '--xmls-testrun-id',
        str(testrun_id)
    ]

    import pytest
    logger.info("Generating the XMLs using 'pytest {}'".format(' '.join(args)))
    with _silence_output():
        pytest_retval = pytest.main(args)

    missing_files = []
    for fname in _XML_FILES:
        if not os.path.exists(fname):
            missing_files.append(fname)
    if missing_files:
        raise TestcasesException(
            "The XML files '{}' were not generated".format(' and '.join(missing_files)))

    return pytest_retval
