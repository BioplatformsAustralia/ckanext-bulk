#!/usr/bin/env/python
from setuptools import setup

setup(
    name="ckanext-bulk",
    version="1.6.5",
    description="",
    license="GPL3",
    author="Bioplatforms Australia",
    author_email="help@bioplatforms.com",
    url="https://github.com/BioplatformsAustralia/ckanext-bulk/",
    namespace_packages=["ckanext"],
    packages=["ckanext.bulk"],
    zip_safe=False,
    include_package_data=True,
    package_dir={"ckanext.bulk": "ckanext/bulk"},
    package_data={
        "ckanext.bulk": [
            "*.json",
            "templates/*.html",
            "templates/*/*.html",
            "templates/*/*/*.html",
            "public/*/*.css",
            "public/*/*.js",
        ]
    },
    entry_points="""
        [ckan.plugins]
        bulk = ckanext.bulk.plugins:BulkPlugin
    """,
)
