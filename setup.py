from setuptools import setup, find_packages

setup(
    name='cfme_testcases',
    version='0.1',
    url='https://github.com/mkoura/cfme-testcases',
    description='Create new testrun and upload missing testcases using Polarion XUnit Importer',
    long_description=open('README.rst').read().strip(),
    author='Martin Kourim',
    author_email='mkourim@redhat.com',
    license='GPL',
    packages=find_packages(exclude=('tests',)),
    scripts=['cfme_testcases_upload.py'],
    install_requires=['dump2polarion'],
    keywords=['polarion', 'testing'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7'],
    include_package_data=True
)