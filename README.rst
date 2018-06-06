Moved to https://gitlab.com/mkourim/cfme-testcases
==============

Usage
-----
Create new test run in Polarion and upload missing test cases. Run in the ManageIQ ``integration_tests`` directory in your usual virtual environment.

.. code-block::

    cfme_testcases_upload.py -t {testrun id}

Install
-------
You don't need to install the package, you can use the scripts directly from the cloned repository.

To install the package to your virtualenv, run

.. code-block::

    pip install .

Requirements
------------
You need ``dump2polarion``.
