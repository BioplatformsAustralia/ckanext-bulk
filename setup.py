#!/usr/bin/env/python
from setuptools import setup

setup(
    name='ckanext-bulk',
    version='0.9.0',
    description='',
    license='GPL3',
    author='CCG, Murdoch University',
    author_email='tech@ccg.murdoch.edu.au',
    url='https://github.com/muccg/ckanext-bulk/',
    namespace_packages=['ckanext'],
    packages=['ckanext.bulk'],
    zip_safe=False,
    include_package_data=True,
    package_dir={'ckanext.bulk': 'ckanext/bulk'},
    package_data={'ckanext.bulk': ['*.json', 'templates/*.html', 'templates/*/*.html', 'templates/*/*/*.html', 'static/*.css', 'static/*.png', 'static/*.jpg', 'static/*.css', 'static/*.ico']},
    entry_points = """
        [ckan.plugins]
        bulk = ckanext.bulk.plugins:BulkPlugin
    """
)
