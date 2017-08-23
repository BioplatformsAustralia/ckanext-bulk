
import logging
from ckan.plugins import toolkit, IConfigurer, IRoutes, SingletonPlugin, implements


log = logging.getLogger(__name__)


class WgetPlugin(SingletonPlugin):
    implements(IConfigurer)
    implements(IRoutes, inherit=True)

    def after_map(self, map):
        log.critical("wget URL mapped")
        controller = 'ckanext.wget.controller:WgetController'
        map.connect(
            'wget_filelist',
            '/wget/file_list',
            action='file_list',
            controller=controller)
        return map

    def update_config(self, config):
        toolkit.add_template_directory(config, "templates")
        toolkit.add_public_directory(config, "static")
