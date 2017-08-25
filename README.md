# ckanext-wget

This CKAN extension adds a bulk-download facility to CKAN.

Links can be added to organization search packages, as well
as to the dataset page, which produce a Zip file containing:

  - a list of all relevant resource URLs
  - a MD5 checksum file
  - a shell script which downloads those resources with `wget`, then confirms the checksums match
