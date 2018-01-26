# -*- coding: utf-8 -*-
"""
Utility functions.
"""

from __future__ import absolute_import, unicode_literals

import os

from xml.etree import ElementTree

from cfme_testcases.exceptions import TestcasesException


_NOT_EXPECTED_FORMAT_MSG = 'XML file is not in expected format'


def get_unicode_str(obj):
    """Makes sure obj is a unicode string."""
    try:
        # Python 2.x
        if isinstance(obj, unicode):
            return obj
        if isinstance(obj, str):
            return obj.decode('utf-8', errors='ignore')
        return unicode(obj)
    except NameError:
        # Python 3.x
        if isinstance(obj, str):
            return obj
        if isinstance(obj, bytes):
            return obj.decode('utf-8', errors='ignore')
        return str(obj)


def get_xml_root(xml_file):
    """Returns XML root."""
    try:
        xml_tree = ElementTree.parse(os.path.expanduser(xml_file))
        xml_root = xml_tree.getroot()
    # pylint: disable=broad-except
    except Exception as err:
        raise TestcasesException("Failed to parse XML file '{}': {}".format(xml_file, err))
    return xml_root


def remove_response_property(xml_root):
    """Removes response properties if exist."""
    if xml_root.tag == 'testcases':
        resp_properties = xml_root.find('response-properties')
        if resp_properties is not None:
            xml_root.remove(resp_properties)
    elif xml_root.tag == 'testsuites':
        properties = xml_root.find('properties')
        resp_properties = []
        for prop in properties:
            prop_name = prop.get('name', '')
            if 'polarion-response-' in prop_name:
                resp_properties.append(prop)
        for resp_property in resp_properties:
            properties.remove(resp_property)
    else:
        raise TestcasesException(_NOT_EXPECTED_FORMAT_MSG)


def set_property(xml_root, name, value):
    """Sets property to specified value."""
    properties = xml_root.find('properties')
    for prop in properties:
        if prop.get('name') == name:
            prop.set('value', value)
            break
    else:
        ElementTree.SubElement(properties, 'property',
                               {'name': name, 'value': value})


def set_lookup_method(xml_root, value):
    """Changes lookup method."""
    if xml_root.tag == 'testcases':
        set_property(xml_root, 'lookup-method', value)
    elif xml_root.tag == 'testsuites':
        set_property(xml_root, 'polarion-lookup-method', value)
    else:
        raise TestcasesException(_NOT_EXPECTED_FORMAT_MSG)


def set_dry_run(xml_root):
    """Sets dry-run so records are not updated, only log file is produced."""
    if xml_root.tag == 'testcases':
        set_property(xml_root, 'dry-run', 'true')
    elif xml_root.tag == 'testsuites':
        set_property(xml_root, 'polarion-dry-run', 'true')
    else:
        raise TestcasesException(_NOT_EXPECTED_FORMAT_MSG)


def etree_to_string(xml_root):
    """Returns string representation of element tree."""
    return get_unicode_str(ElementTree.tostring(xml_root, encoding='utf-8'))
