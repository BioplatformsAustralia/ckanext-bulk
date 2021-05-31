# ckanext-bulk

This CKAN extension adds a bulk-download facility to CKAN.

Snippets are provided, which when included on the relevant pages will
add a button that, when clicked, downloads a Zip file containing:

  - a list of all relevant resource URLs
  - a MD5 checksum file
  - scripts which downloads those resources and confirm the checksums match in:
    - Python (cross platform)
    - Windows PowerShell
    - UNIX shell script (bash, using `curl`)
  - CSV files detailing all metadata for each package (one CSV per dataset schema)
  - CSV files detailing all metadata for each resource (one CSV per resource schema)
  - a metadata file containing information about the original query and quantity of results

Snippets are provided for the organization and package search CKAN views.

This extension depends upon [ckanext-scheming](https://github.com/ckan/ckanext-scheming).
