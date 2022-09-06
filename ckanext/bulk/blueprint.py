import logging
import ckan.plugins as p
import ckan.lib.helpers as h
import datetime
import string
import hashlib
from flask import Blueprint
from ckan.common import request, c
from ckan.plugins.toolkit import config
from ckan import model
from ckan.lib.base import abort
from ckan.logic import NotFound, NotAuthorized, get_action, check_access
from ckan.views.group import _db_to_form_schema, _action, _read, _guess_group_type
from collections import OrderedDict
from .zipoutput import generate_bulk_zip

_ = p.toolkit._


log = logging.getLogger(__name__)

bulk = Blueprint("bulk", __name__)


def timestamp():
    return datetime.datetime.now().strftime("%Y%m%dT%H%M")


def make_safe(s):
    return "".join(
        t for t in s if t in string.digits or t in string.ascii_letters or t == "-"
    )


def prefix_from_components(components):
    # note: a hash is generated of the components to avoid long paths
    components = [make_safe(c) for c in components]
    component_hash = hashlib.sha1(("_".join(components)).encode("utf-8")).hexdigest()[
        -8:
    ]
    return "bpa_{}_{}".format(component_hash, timestamp())


def dataset_to_zip_prefix(_id):
    return prefix_from_components([_id])


def query_to_zip_prefix(request, name=None):
    def add_param(c, p):
        v = request.params.get(p, "").strip()
        if v:
            c.append(v)

    components = []
    if name:
        components.append(name)
    add_param(components, "q")
    add_param(components, "res-format")
    add_param(components, "tags")
    return prefix_from_components(components)


def organization_file_list(id):
    limit = p.toolkit.asint(config.get("ckanext.bulk.limit", 100))
    group_type = _guess_group_type()

    context = {
        "model": model,
        "session": model.Session,
        "user": c.user,
        "schema": _db_to_form_schema(group_type=group_type),
        "for_view": True,
        "extras_as_string": True,
    }
    data_dict = {"id": id, "type": group_type}

    # unicode format (decoded from utf8)
    c.q = request.params.get("q", "")

    try:
        # Do not query for the group datasets when dictizing, as they will
        # be ignored and get requested on the controller anyway
        data_dict["include_datasets"] = False
        c.group_dict = _action("group_show")(context, data_dict)
        c.group = context["group"]
    except (NotFound, NotAuthorized):
        abort(404, _("Group not found"))

    _read(id, limit, group_type)

    def _resources():
        for package in c.page.items:
            for resource in package["resources"]:
                yield resource

    name = c.group_dict["name"]
    packages = [t for t in c.page.items]
    resources = list(_resources())

    site_url = config.get("ckan.site_url").rstrip("/")
    query = request.params.get(u"q", u"")
    query_url = "%s%s" % (
        site_url,
        h.add_url_param(
            h.url_for("organization.read", id=id), new_params=request.params
        ),
    )
    download_url = "%s%s" % (
        site_url,
        h.add_url_param(
            h.url_for("bulk.organization_file_list", id=id), new_params=request.params
        ),
    )

    return generate_bulk_zip(
        query_to_zip_prefix(request, name),
        "Search of organization: {}".format(name),
        c.userobj,
        [c.group_dict],
        packages,
        resources,
        query,
        query_url,
        download_url,
    )


def package_search_list():
    limit = p.toolkit.asint(config.get("ckanext.bulk.limit", 100))
    try:
        context = {"model": model, "user": c.user, "auth_user_obj": c.userobj}
        check_access("site_read", context)
    except NotAuthorized:
        abort(403, _("Not authorized to see this page"))

    # unicode format (decoded from utf8)
    q = request.params.get("q", u"")
    c.query_error = False

    c.fields = []
    # c.fields_grouped will contain a dict of params containing
    # a list of values eg {'tags':['tag1', 'tag2']}
    c.fields_grouped = {}
    search_extras = {}
    fq = ""
    for (param, value) in list(request.params.items()):
        if (
            param not in ["q", "page", "sort"]
            and len(value)
            and not param.startswith("_")
        ):
            if not param.startswith("ext_"):
                c.fields.append((param, value))
                fq += ' %s:"%s"' % (param, value)
                if param not in c.fields_grouped:
                    c.fields_grouped[param] = [value]
                else:
                    c.fields_grouped[param].append(value)
            else:
                search_extras[param] = value

    context = {
        "model": model,
        "session": model.Session,
        "user": c.user,
        "for_view": True,
        "auth_user_obj": c.userobj,
        "extras_as_string": True,
    }

    facets = OrderedDict()

    data_dict = {
        "q": q,
        "fq": fq.strip(),
        "facet.field": list(facets.keys()),
        "rows": limit,
        "extras": search_extras,
        "include_private": p.toolkit.asbool(
            config.get("ckan.search.default_include_private", True)
        ),
    }

    query = get_action("package_search")(context, data_dict)
    results = query["results"]

    def _resources():
        for package in results:
            for resource in package["resources"]:
                yield resource

    packages = [t for t in results]
    resources = list(_resources())

    def _organizations():
        orgs = {}
        orgs_with_extras = []

        # get unique orgs by name
        for package in results:
            orgs[package["organization"]["name"]] = package["organization"]["id"]

        for org in list(orgs.items()):
            name = org[0]
            org_dict = {"id": org[1]}

            try:
                # Do not query for the group datasets when dictizing, as they will
                # be ignored and get requested on the controller anyway
                org_dict["include_datasets"] = False
                found_org_dict = get_action("organization_show")(context, org_dict)

            except (NotFound, NotAuthorized):
                abort(404, _("Organization not found"))

            orgs_with_extras.append(found_org_dict)

        return orgs_with_extras

    organizations = _organizations()

    site_url = config.get("ckan.site_url").rstrip("/")
    query_url = "%s%s" % (
        site_url,
        h.add_url_param(h.url_for("dataset.search"), new_params=request.params),
    )
    download_url = "%s%s" % (
        site_url,
        h.add_url_param(
            h.url_for("bulk.package_search_list"), new_params=request.params
        ),
    )

    return generate_bulk_zip(
        query_to_zip_prefix(request),
        "Search of all datasets",
        c.userobj,
        organizations,
        packages,
        resources,
        q,
        query_url,
        download_url,
    )


def package_file_list(id):
    limit = p.toolkit.asint(config.get("ckanext.bulk.limit", 100))

    context = {
        "model": model,
        "session": model.Session,
        "user": c.user,
        "for_view": True,
        "auth_user_obj": c.userobj,
    }
    data_dict = {"id": id, "include_tracking": True}

    # check if package exists
    try:
        pkg_dict = get_action("package_show")(context, data_dict)
    except (NotFound, NotAuthorized):
        abort(404, _("Dataset not found"))

    name = pkg_dict["name"]

    site_url = config.get("ckan.site_url").rstrip("/")
    query = "id:%s" % (name,)
    query_url = "%s%s" % (site_url, h.url_for("dataset.read", id=name))
    download_url = "%s%s" % (site_url, h.url_for("bulk.package_file_list", id=id))

    org_dict = {"id": pkg_dict["organization"]["id"]}
    try:
        # Do not query for the group datasets when dictizing, as they will
        # be ignored and get requested on the controller anyway
        org_dict["include_datasets"] = False
        found_org_dict = get_action("organization_show")(context, org_dict)
    except (NotFound, NotAuthorized):
        abort(404, _("Organization not found"))

    return generate_bulk_zip(
        dataset_to_zip_prefix(id),
        "Dataset: %s" % (name,),
        c.userobj,
        [found_org_dict],
        [pkg_dict],
        pkg_dict["resources"],
        query,
        query_url,
        download_url,
    )


bulk.add_url_rule(
    u"/bulk/organization/<id>/file_list",
    view_func=organization_file_list,
    methods=[u"GET", u"POST"],
)
bulk.add_url_rule(
    u"/bulk/dataset/<id>/file_list",
    view_func=package_file_list,
    methods=[u"GET", u"POST"],
)
bulk.add_url_rule(
    u"/bulk/dataset/file_list", view_func=package_search_list, methods=[u"GET", u"POST"]
)
