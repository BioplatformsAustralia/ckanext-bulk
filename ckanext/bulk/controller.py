import logging
import ckan.plugins as p
from ckan.common import request, c
from pylons import config
from ckan import model
from ckan.lib.base import abort, BaseController
from ckan.controllers.organization import OrganizationController
from ckan.logic import NotFound, NotAuthorized, get_action
from .zipoutput import generate_bulk_zip

_ = p.toolkit._


log = logging.getLogger(__name__)


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

        def _resources():
            for package in c.page.items:
                for resource in package['resources']:
                    yield resource

        name = c.group_dict['name']
        packages = [t for t in c.page.items]
        resources = list(_resources())

        return generate_bulk_zip(
            name,
            'Search of organization: {}'.format(name),
            c.userobj,
            packages,
            resources)


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
        return generate_bulk_zip(name, 'Dataset: %s' % (name,), c.userobj, [pkg_dict], pkg_dict['resources'])
