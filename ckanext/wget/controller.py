import logging
import ckan.plugins as p
from ckan.common import response

_ = p.toolkit._


log = logging.getLogger(__name__)


class WgetController(p.toolkit.BaseController):
    controller = 'ckanext.wget.controller:WgetController'

    def file_list(self, *args, **kwargs):
        response.headers['Content-Type'] = 'text/plain'
        return "hello world"
