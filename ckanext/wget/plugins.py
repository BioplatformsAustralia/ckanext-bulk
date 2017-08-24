
import logging
from ckan.plugins import toolkit, IConfigurer, IRoutes, SingletonPlugin, implements


log = logging.getLogger(__name__)


class WgetPlugin(SingletonPlugin):
    implements(IConfigurer)
    implements(IRoutes, inherit=True)

    def after_map(self, map):
        org_controller = 'ckanext.wget.controller:WgetOrganizationController'
        map.connect(
            'file_list',
            '/wget/organization/{id}/file_list',
            action='file_list',
            controller=org_controller)
        return map

    def update_config(self, config):
        toolkit.add_template_directory(config, "templates")
        toolkit.add_public_directory(config, "static")
