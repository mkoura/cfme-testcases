from setuptools import find_packages, setup

setup(
    name='cfme_testcases',
    version='0.2',
    url='https://github.com/mkoura/cfme-testcases',
    description='Create new testrun and upload missing testcases using Polarion Importers',
    long_description=open('README.rst').read().strip(),
    author='Martin Kourim',
    author_email='mkourim@redhat.com',
    license='GPL',
    packages=find_packages(exclude=('tests',)),
    scripts=['cfme_testcases_upload.py'],
    install_requires=['pytest', 'dump2polarion>=0.19'],
    keywords=['polarion', 'testing'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Intended Audience :: Developers'],
    include_package_data=True
)
