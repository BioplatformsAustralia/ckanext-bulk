import logging
from ckan.plugins import toolkit, IConfigurer, IBlueprint, SingletonPlugin, implements

from ckanext.bulk import blueprint


log = logging.getLogger(__name__)


class BulkPlugin(SingletonPlugin):
    implements(IConfigurer)
    implements(IBlueprint)

    # IConfigurer
    def update_config(self, config):
        toolkit.add_template_directory(config, "templates")
        toolkit.add_public_directory(config, "static")

    # IBlueprint
    def get_blueprint(self):
        return blueprint.bulk
