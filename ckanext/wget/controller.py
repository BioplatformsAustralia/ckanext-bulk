import re
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
from zipfile import ZipFile, ZIP_DEFLATED
from io import BytesIO

_ = p.toolkit._


log = logging.getLogger(__name__)


WGET_EXPLANATORY_NOTE = '''\
CKAN Bulk Download
------------------

Bulk download generated: %(timestamp)s
Bulk download context: %(title)s

This archive contains the following files:

urls.txt:
A list of all URLs matching the CKAN search you performed.

md5sum.txt:
MD5 checksums for all files.

download.sh:
UNIX shell script, which when executed will download the files,
and then checksum then. This should operate correctly on any
Linux distribution, so long as 'wget' and 'md5sum' are installed.
'''


def get_timestamp():
    return datetime.datetime.now(
        h.get_display_timezone()).strftime('%Y-%m-%dT%H:%M:%S.%f%z')


def bulk_download_zip(title, pfx, urls):
    def ip(s):
        return pfx + '/' + s

    response.headers['Content-Type'] = 'application/zip'
    fd = BytesIO()
    zf = ZipFile(fd, mode='w', compression=ZIP_DEFLATED)
    zf.writestr(ip('README.txt'), WGET_EXPLANATORY_NOTE % {

    });
    zf.writestr(ip('urls.txt'), u'\n'.join(urls) + u'\n')
    zf.writestr(ip('download.sh'), '#!/bin/bash\n\nwget -i urls.txt')
    zf.close()
    return fd.getvalue()


class WgetOrganizationController(OrganizationController):
    controller = 'ckanext.wget.controller:WgetOrganizationController'
    group_types = ['organization']

    def __init__(self, *args, **kwargs):
        super(WgetOrganizationController, self).__init__(*args, **kwargs)
        self.limit = p.toolkit.asint(config.get('ckanext.wget.limit', 100))

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
            raise
            abort(404, _('Group not found'))

        self._read(id, self.limit, group_type)

        urls = []
        for package in c.page.items:
            for resource in package['resources']:
                urls.append(resource['url'])

        return bulk_download_zip(urls)


class WgetPackageController(BaseController):
    controller = 'ckanext.wget.controller:WgetPackageController'

    def __init__(self, *args, **kwargs):
        super(WgetPackageController, self).__init__(*args, **kwargs)
        self.limit = p.toolkit.asint(config.get('ckanext.wget.limit', 100))

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

        urls = []
        for resource in pkg_dict['resources']:
            urls.append(resource['url'])

        return bulk_download_zip(urls)
