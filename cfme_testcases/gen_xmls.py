# -*- coding: utf-8 -*-
"""
Run pytest --collect-only and generate XMLs.
"""

from __future__ import absolute_import, unicode_literals

import logging
import os
import subprocess
import sys

from cfme_testcases.exceptions import TestcasesException


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


_XML_FILES = ('test_case_import.xml', 'test_run_import.xml')


def _check_environment():
    # check that launched in integration tests repo
    if not os.path.exists('cfme/tests'):
        raise TestcasesException('Not running in the integration tests repo')
    # check that running in virtualenv
    if not hasattr(sys, 'real_prefix'):
        raise TestcasesException('Not running in virtual environment')


def _cleanup():
    for fname in _XML_FILES:
        try:
            os.remove(fname)
        except OSError:
            pass


def run_pytest(testrun_id):
    """Runs the pytest command."""
    pytest_retval = None
    _check_environment()
    _cleanup()

    args = [
        'miq-runtest',
        '-qq',
        '--collect-only',
        '--long-running',
        '--perf',
        '--runxfail',
        '--use-provider', 'complete',
        '--generate-legacy-xmls',
        '--xmls-testrun-id',
        str(testrun_id)
    ]

    logger.info("Generating the XMLs using '%s'", ' '.join(args))
    with open(os.devnull, 'w') as devnull:
        pytest_proc = subprocess.Popen(args, stdout=devnull, stderr=devnull)
        try:
            pytest_retval = pytest_proc.wait()
        # pylint: disable=broad-except
        except Exception:
            try:
                pytest_proc.terminate()
            except OSError:
                pass
            pytest_proc.wait()
            return None

    missing_files = []
    for fname in _XML_FILES:
        if not os.path.exists(fname):
            missing_files.append(fname)
    if missing_files:
        raise TestcasesException(
            'The XML files {} were not generated'.format(' and '.join(missing_files)))

    return pytest_retval
