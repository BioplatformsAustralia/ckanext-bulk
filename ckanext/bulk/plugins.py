
import logging
from ckan.plugins import toolkit, IConfigurer, IRoutes, SingletonPlugin, implements


log = logging.getLogger(__name__)


class BulkPlugin(SingletonPlugin):
    implements(IConfigurer)
    implements(IRoutes, inherit=True)

    def after_map(self, map):
        org_controller = 'ckanext.bulk.controller:BulkOrganizationController'
        map.connect(
            'bulk_organization_file_list',
            '/bulk/organization/{id}/file_list',
            action='file_list',
            controller=org_controller)
        pkg_controller = 'ckanext.bulk.controller:BulkPackageController'
        map.connect(
            'bulk_package_file_list',
            '/bulk/dataset/{id}/file_list',
            action='file_list',
            controller=pkg_controller)
        return map

    def update_config(self, config):
        toolkit.add_template_directory(config, "templates")
        toolkit.add_public_directory(config, "static")
