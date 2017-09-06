import datetime
import logging
import ckan.plugins as p
import ckan.lib.helpers as h
from pylons import config
from ckan import model
from ckan.lib.base import abort, BaseController
from ckan.controllers.organization import OrganizationController
from ckan.common import request, response, c
from ckan.logic import NotFound, NotAuthorized, get_action
from urlparse import urlparse
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from io import BytesIO

_ = p.toolkit._


log = logging.getLogger(__name__)


SH_TEMPLATE = '''\
#!/bin/sh

#
# This UNIX shell script was automatically generated.
#

if [ x"$CKAN_API_KEY" = "x" ]; then
  echo "Please set the CKAN_API_KEY environment variable."
  echo
  echo "You can find your API Key by browsing to:"
  echo "__USER_PAGE__"
  echo
  echo "The API key has the format:"
  echo "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  exit 1
fi

if ! which wget >/dev/null 2>&1; then
  echo "`wget` is not installed. Please install it."
  echo
  echo "On MacOS, it can be installed via HomeBrew (https://brew.sh/)"
  echo "using the command `brew install wget`"
  exit 1
fi

echo "Downloading data"
wget --no-http-keep-alive --header="Authorization: $CKAN_API_KEY" -c -t 0 -i urls.txt

echo "Data download complete. Verifying checksums:"
md5sum -c md5sum.txt 2>&1 | tee md5sums.log
'''


POWERSHELL_TEMPLATE = '''\
#!/usr/bin/powershell

$apikey = $Env:CKAN_API_KEY
if (!$apikey) {
  "Please set the CKAN_API_KEY environment variable."
  ""
  "You can find your API Key by browsing to:"
  "__USER_PAGE__"
  ""
  "The API key has the format:"
  "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  exit 1
}

#
# This PowerShell script was automatically generated.
#

function DownloadURL($url)
{
    $filename = $url.Substring($url.lastIndexOf('/') + 1)
    if (Test-Path $filename) {
        "File already exists, skipping download: " + $filename
        return
    }
    $client = new-object System.Net.WebClient
    $client.Headers.Add('Authorization: ' + $apikey)
    "Downloading: " + $filename
    $client.DownloadFile($url, $filename)
}

function VerifyMD5([String]$filename, [String]$expected_md5)
{
    $md5hash = new-object -TypeName System.Security.Cryptography.MD5CryptoServiceProvider
    try {
        $actual_md5 = [System.BitConverter]::ToString($md5hash.ComputeHash([System.IO.File]::ReadAllBytes($filename))).Replace('-', '').toLower();
    } catch [System.IO.FileNotFoundException] {
        $filename + ": FAILED open or read"
        return
    }
    if ($actual_md5 -eq $expected_md5) {
        $filename + ": OK"
    } else {
        $filename + ": FAILED"
    }
}


"Commencing bulk download of data from CKAN"
""

$urls = Get-Content 'urls.txt'
ForEach ($line in $urls) {
    DownloadURL $line
}

"File downloads complete."
""
"Verifying file checksums"
""
$md5s = Get-Content 'md5sum.txt'
ForEach ($line in $md5s) {
    $md5, $filename = $line.Split(" ",[StringSplitOptions]'RemoveEmptyEntries')
    VerifyMD5 $filename $md5
}
'''


BULK_EXPLANATORY_NOTE = '''\
CKAN Bulk Download
------------------

{title}

Bulk download package generated:
{timestamp}

Bulk download authorised for user:
{user}

This archive contains the following files:

urls.txt:
A list of all URLs matching the CKAN search you performed.

md5sum.txt:
MD5 checksums for all files.

download.ps1:
Windows PowerShell script, which when executed will download the files,
and then checksum them. There are no dependencies other than PowerShell.

download.sh:
UNIX shell script, which when executed will download the files,
and then checksum then. This is supported on any Linux or MacOS/BSD
system, so long as `wget` is installed.
'''


def get_timestamp():
    return datetime.datetime.now(
        h.get_display_timezone()).strftime('%Y-%m-%dT%H:%M:%S.%f%z')


def bulk_download_zip(pfx, title, user, resource_iter):
    def ip(s):
        return pfx + '/' + s

    def write_script(filename, contents):
        info = ZipInfo(ip(filename))
        info.external_attr = 0755 << 16L
        # we don't use python format-strings as the powershell syntax collides
        site_url = config.get('ckan.site_url').rstrip('/')
        user_url = h.url_for(controller='user', action='read', id=user.name)
        contents = contents.replace("__USER_PAGE__", '%s/%s' % (site_url, user_url))
        zf.writestr(info, contents.encode('utf-8'))

    urls = []
    md5sums = []

    md5_attribute = config.get('ckanext.bulk.md5_attribute', 'md5')
    for resource in sorted(resource_iter, key=lambda r: r['url']):
        url = resource['url']
        urls.append(resource['url'])
        if md5_attribute in resource:
            filename = urlparse(url).path.split('/')[-1]
            md5sums.append((resource[md5_attribute], filename))

    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = str('attachment; filename="%s.zip"' % pfx)
    fd = BytesIO()
    zf = ZipFile(fd, mode='w', compression=ZIP_DEFLATED)
    zf.writestr(ip('README.txt'), BULK_EXPLANATORY_NOTE.format(
        timestamp=get_timestamp(),
        title=title,
        user='%s (%s, %s)' % (user.fullname, user.name, user.email)))
    zf.writestr(ip('urls.txt'), u'\n'.join(urls) + u'\n')
    zf.writestr(ip('md5sum.txt'), u'\n'.join('%s  %s' % t for t in md5sums))

    write_script('download.sh', SH_TEMPLATE)
    write_script('download.ps1', POWERSHELL_TEMPLATE)

    zf.close()
    return fd.getvalue()


class BulkOrganizationController(OrganizationController):
    controller = 'ckanext.bulk.controller:BulkOrganizationController'
    group_types = ['organization']

    def __init__(self, *args, **kwargs):
        super(BulkOrganizationController, self).__init__(*args, **kwargs)
        self.limit = p.toolkit.asint(config.get('ckanext.bulk.limit', 100))

    def file_list(self, id):
        group_type = self._ensure_controller_matches_group_type(
            id.split('@')[0])

        context = {
            'model': model,
            'session': model.Session,
            'user': c.user,
            'schema': self._db_to_form_schema(group_type=group_type),
            'for_view': True
        }
        data_dict = {'id': id, 'type': group_type}

        # unicode format (decoded from utf8)
        c.q = request.params.get('q', '')

        try:
            # Do not query for the group datasets when dictizing, as they will
            # be ignored and get requested on the controller anyway
            data_dict['include_datasets'] = False
            c.group_dict = self._action('group_show')(context, data_dict)
            c.group = context['group']
        except (NotFound, NotAuthorized):
            abort(404, _('Group not found'))

        self._read(id, self.limit, group_type)

        def _resource_iter():
            for package in c.page.items:
                for resource in package['resources']:
                    yield resource

        name = c.group_dict['name']
        return bulk_download_zip(name, 'Search of organization: %s' % (name,), c.userobj, _resource_iter())


class BulkPackageController(BaseController):
    controller = 'ckanext.bulk.controller:BulkPackageController'

    def __init__(self, *args, **kwargs):
        super(BulkPackageController, self).__init__(*args, **kwargs)
        self.limit = p.toolkit.asint(config.get('ckanext.bulk.limit', 100))

    def file_list(self, id):
        context = {
            'model': model,
            'session': model.Session,
            'user': c.user,
            'for_view': True,
            'auth_user_obj': c.userobj
        }
        data_dict = {
            'id': id,
            'include_tracking': True
        }

        # check if package exists
        try:
            pkg_dict = get_action('package_show')(context, data_dict)
        except (NotFound, NotAuthorized):
            abort(404, _('Dataset not found'))

        name = pkg_dict['name']
        return bulk_download_zip(name, 'Dataset: %s' % (name,), c.userobj, pkg_dict['resources'])
