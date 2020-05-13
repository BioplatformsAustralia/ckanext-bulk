import jinja2
import ckan.lib.helpers as h
import sys
import datetime
import csv
from collections import defaultdict
from StringIO import StringIO
from pylons import config
from urlparse import urlparse
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from ckan.common import response
from io import BytesIO
from .bash import SH_TEMPLATE
from .powershell import POWERSHELL_TEMPLATE
from ckanext.scheming.helpers import scheming_get_dataset_schema


BULK_EXPLANATORY_NOTE = """\
CKAN Bulk Download
------------------

{title} {prefix}

Bulk download package generated:
{timestamp}

This archive contains the following files:

download.ps1:
Windows PowerShell script, which when executed will download the files,
and then checksum them. There are no dependencies other than PowerShell.

download.sh:
UNIX shell script, which when executed will download the files,
and then checksum them. This is supported on any Linux or MacOS/BSD
system, so long as `curl` is installed.

package_metadata folder:
Contains metadata spreadsheets for all selected data packages, grouped by
the type of package (schema). Each data package will contain one or more
resources.

resource_metadata folder:
Contains metadata spreadsheets for all selected data resources (files).

tmp folder:
This folder contains files required by the download scripts. Its
contents can be ignored.
"""


def str_crlf(s):
    """
    convert string to DOS multi-line encoding (CRLF)
    """
    return s.replace("\n", "\r\n")


def get_timestamp():
    return datetime.datetime.now(h.get_display_timezone()).strftime(
        "%Y-%m-%dT%H:%M:%S.%f%z"
    )


def objects_by_attr(objects, attr, default):
    by_attr = defaultdict(list)
    for obj in objects:
        by_attr[obj.get(attr, default)].append(obj)
    return by_attr


def debug(s):
    sys.stderr.write(repr(s))
    sys.stderr.write("\n")
    sys.stderr.flush()


def schema_to_csv(typ, schema_key, objects):
    # Note: as we're in Python 2, we have to do a bit of a dance here with unicode --
    # we must make sure everything we put into the writer has been encoded
    schema = scheming_get_dataset_schema(typ)
    if schema is None:
        # some objects may not have a ckanext-scheming schema
        return ""
    fd = StringIO()
    w = csv.writer(fd)
    header = []
    field_names = []
    for field in schema[schema_key]:
        field_names.append(field["field_name"])
        header.append(field["label"].encode("utf8"))
    w.writerow(header)
    for obj in sorted(objects, key=lambda p: p["name"]):
        w.writerow(
            [encode_field(obj.get(field_name, "")) for field_name in field_names]
        )
    return fd.getvalue()


def encode_field(field_name):
    # fix for AttributeError: 'int' object has no attribute 'encode'
    if isinstance(field_name, (int, long, float)):
        field_name = str(field_name)
    return field_name.encode("utf8")


def generate_bulk_zip(pfx, title, user, packages, resources):
    def ip(s):
        return pfx + "/" + s

    def write_script(filename, contents):
        info = ZipInfo(ip(filename))
        info.external_attr = 0755 << 16L  # mark script as executable
        user_page = None
        if user:
            site_url = config.get("ckan.site_url").rstrip("/")
            user_page = "%s/%s" % (
                site_url,
                h.url_for(controller="user", action="read", id=user.name),
            )
        contents = (
            jinja2.Environment()
            .from_string(contents)
            .render(
                user_page=user_page, md5sum_fname=md5sum_fname, urls_fname=urls_fname
            )
        )
        zf.writestr(info, contents.encode("utf-8"))

    urls = []
    md5sums = []

    md5_attribute = config.get("ckanext.bulk.md5_attribute", "md5")
    for resource in sorted(resources, key=lambda r: r["url"]):
        url = resource["url"]
        urls.append(resource["url"])
        if md5_attribute in resource:
            filename = urlparse(url).path.split("/")[-1]
            md5sums.append((resource[md5_attribute], filename))

    response.headers["Content-Type"] = "application/zip"
    response.headers["Content-Disposition"] = str('attachment; filename="%s.zip"' % pfx)
    fd = BytesIO()
    zf = ZipFile(fd, mode="w", compression=ZIP_DEFLATED)
    zf.writestr(
        ip("README.txt"),
        str_crlf(
            BULK_EXPLANATORY_NOTE.format(
                prefix=pfx, timestamp=get_timestamp(), title=title
            )
        ),
    )

    urls_fname = "tmp/{}_urls.txt".format(pfx)
    md5sum_fname = "tmp/{}_md5sum.txt".format(pfx)

    zf.writestr(ip(urls_fname), u"\n".join(urls) + u"\n")
    zf.writestr(ip(md5sum_fname), u"\n".join("%s  %s" % t for t in md5sums) + u"\n")

    for typ, typ_packages in objects_by_attr(packages, "type", "unknown").items():
        # some objects may not have a ckanext-scheming schema
        if typ is None:
            continue
        zf.writestr(
            ip("package_metadata/package_metadata_{}_{}.csv".format(pfx, typ)),
            schema_to_csv(typ, "dataset_fields", typ_packages),
        )

    for typ, typ_resources in objects_by_attr(
        resources, "resource_type", "unknown"
    ).items():
        # some objects may not have a ckanext-scheming schema
        if typ is None:
            continue
        zf.writestr(
            ip("resource_metadata/resource_metadata_{}_{}.csv".format(pfx, typ)),
            schema_to_csv(typ, "resource_fields", typ_resources),
        )

    write_script("download.sh", SH_TEMPLATE)
    write_script("download.ps1", POWERSHELL_TEMPLATE)

    zf.close()
    return fd.getvalue()
