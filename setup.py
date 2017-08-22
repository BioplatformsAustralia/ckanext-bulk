#!/usr/bin/env/python
from setuptools import setup

setup(
    name='ckanext-wget',
    version='0.1.0',
    description='',
    license='AGPL3',
    author='CCG, Murdoch University',
    author_email='tech@ccg.murdoch.edu.au',
    url='https://github.com/muccg/ckanext-wget/',
    namespace_packages=['ckanext'],
    packages=['ckanext.wget'],
    zip_safe=False,
    include_package_data=True,
    package_dir={'ckanext.wget': 'ckanext/wget'},
    package_data={'ckanext.wget': ['*.json', 'templates/*.html', 'templates/*/*.html', 'templates/*/*/*.html', 'static/*.css', 'static/*.png', 'static/*.jpg', 'static/*.css', 'static/*.ico']},
    entry_points = """
        [ckan.plugins]
        wget = ckanext.wget.plugins:WgetPlugin
    """
)
