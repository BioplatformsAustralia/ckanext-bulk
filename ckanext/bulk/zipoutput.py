import jinja2
import ckan.lib.helpers as h
import sys
import datetime
import codecs
import csv
import bitmath
import os
import ckan.plugins.toolkit as tk
from collections import defaultdict
from ckan.plugins.toolkit import config
from urllib.parse import urlparse
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from flask import make_response
from io import BytesIO, TextIOWrapper
from .bash import SH_TEMPLATE
from .powershell import POWERSHELL_TEMPLATE
from .python import PY_TEMPLATE
from ckanext.scheming.helpers import scheming_get_dataset_schema

BULK_EXPLANATORY_NOTE = """\
CKAN Bulk Download
------------------

{title} {prefix}

Bulk download package generated: {timestamp}
Number of Organizations        : {organization_count}
Number of Packages             : {package_count}
Number of Resources            : {resource_count}
Total Space required           : {total_size} {includes_optional}
Total Size (bytes)             : {total_size_bytes}

This archive and associated scripts have been generated to assist
with the downloading of files from the Bioplatforms Australia Data Portal.

This archive contains the following files:

download.py:
Python 3 script, which when executed will download the files,
and then checksum them.  This script is cross platform and is supported
on Linux / MacOS / Windows hosts. Requires the `requests` module.

download.ps1:
Windows PowerShell script, which when executed will download the files,
and then checksum them. There are no dependencies other than PowerShell.

download.sh:
UNIX shell script, which when executed will download the files,
and then checksum them. This is supported on any Linux or MacOS/BSD
system, so long as `curl` is installed.

Before running either of these scripts, please set the CKAN_API_TOKEN
environment variable.

You need to create your API TOKEN within the data portal and copy/save it.
You then use this token whenever you wish to download
data from the data portal.

You can create your API Token by browsing to:
{user_page}, and clicking the API Tokens tab.
Enter a name for your token, then click "Create API Token".

The API key of the format:
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
is now obsolete, and you should use the instructions above to 
create your new API token.
 
To set the environment variable in Linux/MacOS/Unix, use:
export CKAN_API_TOKEN=xxxxxxxxxxxxxxxxxxx

On Microsoft Windows, within Powershell, use:
$env:CKAN_API_TOKEN="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"


organization_metadata folder:
Contains metadata spreadsheets as CSV for all organizations owning the
selected data resources (files).

package_metadata folder:
Contains metadata spreadsheets as CSV for all selected data packages, grouped
by the type of package (schema). Each data package will contain one or more
resources. This metadata is an amalgamation of all metadata, including
sample contextual metadata and processing metadata.

resource_metadata folder:
Contains metadata spreadsheets as CSV for all selected data resources (files).

QUERY.txt:
Text file which contains metadata about the download results and the original
query

MEMBERSHIPS.txt:
Text file which contains information about the organization memberships
you hold and those required to access these datasets

OPTIONAL.txt:
(when present) Text file which contains information about the process
to download any files considered optional.

tmp folder:
This folder contains files required by the download scripts. Its
contents can be ignored.


Note all CSV files are encoded as UTF-8 with a Byte Order Mark (BOM) to
enable character set detection by recent versions of Microsoft Excel.
"""

QUERY_TEMPLATE = """\
Title                  : {title}
Prefix                 : {prefix}
Timestamp              : {timestamp}
User Page              : {user_page}
Query                  : {query}
QueryURL               : {query_url}
Download URL           : {download_url}
URL Count              : {url_count}
MD5 Sum Count          : {md5_count}
URL Count Optional     : {url_optional_count}
MD5 Sum Count Optional : {md5_optional_count}
Organization Count     : {organization_count}
Package Count          : {package_count}
Resource Count         : {resource_count}
Shared Files           : {shared_files_count}
Total Space            : {total_size}
Total Bytes            : {total_size_bytes}
"""

OPTIONAL_NOTE = """\
This archive contains details about optional files associated with your
query to the Bioplatforms Australia Data Portal.

These files are considered optional for typical bioinformatics use cases
as they may be:

* Raw data from the machine that generated the data provided to
  allow future reprocessing
* Large in size

Please consult help@bioplatforms.com if you have any queries.

To download these optional files, run the download script with the -o
flag.

For example:
    download.py -o

     or

    download.sh -o

     or

    download.ps1 -o
"""

amd_data_types = [
    "base-genomics-amplicon",
    "base-genomics-amplicon-control",
    "base-metagenomics",
    "base-site-image",
    "mm-genomics-amplicon",
    "mm-genomics-amplicon-control",
    "mm-metagenomics",
    "mm-metatranscriptome",
    "amdb-metagenomics-novaseq",
    "amdb-metagenomics-novaseq-control",
    "amdb-genomics-amplicon",
    "amdb-genomics-amplicon-control",
]

# these are labels that should always be included over their corresponding 'less descriptive' field_name
mandatory_field_labels = [
    "Organization",
    "Title",
    "Description",
    "URL",
    "Tags",
    "Geospatial Coverage",
    "License",
    "Resource Permissions",
]


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


def choose_header_label(typ, schema_key, field):
    field_label = field["label"].encode("utf8")
    if (
        schema_key == "dataset_fields"
        and typ in amd_data_types
        and field_label not in mandatory_field_labels
    ):
        return field["field_name"]
    else:
        return field_label


def org_with_extras_to_csv(org):
    # we must make sure everything we put into the writer has been encoded
    fd = BytesIO()

    # Write the Byte Order Mark to signal to Excel that this CSV is in UTF-8
    fd.write(codecs.BOM_UTF8)

    if sys.version_info >= (3, 0):
        t = TextIOWrapper(fd, write_through = True, encoding='utf-8')
        w = csv.writer(t)
    else:
        w = csv.writer(fd)

    header = []
    field_names = ["key", "value"]
    header.append("Field")
    header.append("Value")
    w.writerow(header)

    w.writerow(["name", encode_field(org["name"])])
    w.writerow(["display_name", encode_field(org["display_name"])])
    for extra in org["extras"]:
        if extra["state"] == "active" or extra["state"] is None:
            w.writerow(
                [encode_field(extra.get(field_name, "")) for field_name in field_names]
            )
    return fd.getvalue()


def schema_to_csv(typ, schema_key, objects):
    # we must make sure everything we put into the writer has been encoded
    schema = scheming_get_dataset_schema(typ)
    if schema is None:
        # some objects may not have a ckanext-scheming schema
        return ""
    fd = BytesIO()

    # Write the Byte Order Mark to signal to Excel that this CSV is in UTF-8
    fd.write(codecs.BOM_UTF8)

    if sys.version_info >= (3, 0):
        t = TextIOWrapper(fd, write_through = True, encoding='utf-8')
        w = csv.writer(t)
    else:
        w = csv.writer(fd)

    header = []
    field_names = []
    for field in schema[schema_key]:
        field_names.append(field["field_name"])
        header.append(encode_field(choose_header_label(typ, schema_key, field)))
    w.writerow(header)
    for obj in sorted(objects, key=lambda p: p["name"]):
        w.writerow(
            [encode_field(obj.get(field_name, "")) for field_name in field_names]
        )
    return fd.getvalue()


def encode_field(field_name):
    # fix for AttributeError: 'int' object has no attribute 'encode'
    if isinstance(field_name, (int, float)):
        field_name = str(field_name)
    if sys.version_info >= (3, 0) and isinstance(field_name, str):
        return field_name
    else:
        return field_name.decode("utf8")


def generate_memberships_information(
    prefix,
    timestamp,
    title,
    user_page,
    organization_count,
    memberships,
    access_required,
):
    def _requestable(organization):
        # Must be visible in our organization lists to be requestable

        # Depends on ytp-request here
        requestable = tk.get_action('get_available_organizations')({}, {})

        org_allowed = False

        for org in requestable:
            if organization['name'] == org['name']:
                org_allowed = True
                break

        # check if Private as well
        for extra in organization.get("extras",[]):
            if extra.get("key") == "Private" and extra.get("value") == "True":
                org_allowed = False
        return org_allowed

    site_description = config.get("ckan.site_description")
    email = os.environ.get('BIOPLATFORMS_HELPDESK_ADDRESS',config.get('error_email_from', ""))

    # work out the request url
    site_url = config.get("ckan.site_url").rstrip("/")
    request_url = "%s%s" % (
        site_url,
        h.url_for("member_request.new"),
    )

    manual_orgs = []
    output = "Membership information for %s \n" % (user_page)

    if memberships is not None and len(memberships):
        output += "For the %s, you are a member of the \nfollowing organisations:\n" % (site_description,)
        for org in memberships:
          output += "    %s\n" % org.get("display_name",org.get("name",""))
    else:
        output += "For the %s, you are a not a member of any organisations\n" % (site_description,)
        output += "\n"
        output += "Please join at %s\n"

    output += "\n"

    if len(access_required):
        output += "To access this data you are required to be a member of the\n"
        output += "following organisations:\n"

        display_url = False

        for org in access_required:
            if _requestable(org):
                output += "    %s\n" % org.get("display_name",org.get("name",""))
                display_url = True
            else:
                manual_orgs.append(org)
        if display_url:
            output += "\n"
            output += "    - Request access to the above organisation(s) at\n"
            output += "          %s\n" % (request_url,)

    if len(manual_orgs):
        if display_url:
            output += "\n"

        for org in manual_orgs:
            output += "    %s\n" % org.get("display_name",org.get("name",""))

        output += "\n"
        output += "    - Please request access to the above organisation(s) via an email to:\n"
        output += "          %s\n" % (email,)


    return output


def generate_bulk_zip(
    pfx,
    title,
    user,
    memberships,
    access_required,
    organizations,
    packages,
    resources,
    query=None,
    query_url=None,
    download_url=None,
):
    user_page = None
    username = ""
    includes_optional = ""
    site_url = config.get("ckan.site_url").rstrip("/")
    if user:
        user_page = "%s%s" % (
            site_url,
            h.url_for("user.read", id=user.name),
        )
        username = user.name

    def str2bool(v):
        if type(v)==bool:
            return v
        if v.lower() in ("yes", "true", "t", "y", "1"):
            return True
        return False

    def ip(s):
        return pfx + "/" + s

    def write_script(filename, contents):
        info = ZipInfo(ip(filename))
        info.external_attr = 0o755 << 16  # mark script as executable
        contents = (
            jinja2.Environment()
            .from_string(contents)
            .render(
                user_page=user_page,
                md5sum_fname=md5sum_fname,
                urls_fname=urls_fname,
                md5sum_optional_fname=md5sum_optional_fname,
                urls_optional_fname=urls_optional_fname,
                prefix=pfx,
                username=username,
            )
        )
        zf.writestr(info, contents.encode("utf-8"))

    urls = []
    md5sums = []
    urls_optional = []
    md5sums_optional = []
    shared_files = []
    total_size_bytes = 0
    resource_count = len(resources)
    package_count = len(packages)
    organization_count = len(organizations)

    md5_attribute = config.get("ckanext.bulk.md5_attribute", "md5")
    for resource in sorted(resources, key=lambda r: r["url"]):
        optional = False
        shared = False

        url = resource["url"]

        if "shared_file" in resource:
            if str2bool(resource["shared_file"]):
                shared = True

                if url in shared_files:
                    continue

                shared_files.append(url)

        if "optional_file" in resource:
            if str2bool(resource["optional_file"]):
                optional = True

        if optional:
            urls_optional.append(url)
        else:
            urls.append(url)

        if "size" in resource:
            if resource["size"]:
                total_size_bytes = total_size_bytes + resource["size"]

        if md5_attribute in resource:
            filename = urlparse(url).path.split("/")[-1]
            if optional:
                md5sums_optional.append((resource[md5_attribute], filename))
            else:
                md5sums.append((resource[md5_attribute], filename))

    if len(urls_optional):
        includes_optional = "(includes optional)"

    shared_files_count = len(shared_files)

    headers = {
        "Content-Type": "application/zip",
        "Content-Disposition": str('attachment; filename="%s.zip"' % pfx),
    }

    fd = BytesIO()
    zf = ZipFile(fd, mode="w", compression=ZIP_DEFLATED)
    zf.writestr(
        ip("README.txt"),
        str_crlf(
            BULK_EXPLANATORY_NOTE.format(
                prefix=pfx,
                timestamp=get_timestamp(),
                title=title,
                user_page=user_page,
                total_size=bitmath.Byte(bytes=total_size_bytes).best_prefix().format("{value:.2f} {unit}"),
                organization_count=organization_count,
                resource_count=resource_count,
                package_count=package_count,
                total_size_bytes=total_size_bytes,
                includes_optional=includes_optional,
            )
        ),
    )

    urls_fname = "tmp/{}_urls.txt".format(pfx)
    md5sum_fname = "tmp/{}_md5sum.txt".format(pfx)

    urls_optional_fname = "tmp/{}_urls_optional.txt".format(pfx)
    md5sum_optional_fname = "tmp/{}_md5sum_optional.txt".format(pfx)

    zf.writestr(ip(urls_fname), "\n".join(urls) + "\n")
    zf.writestr(ip(md5sum_fname), "\n".join("%s  %s" % t for t in md5sums) + "\n")

    if len(urls_optional):
        zf.writestr(ip(urls_optional_fname), "\n".join(urls_optional) + "\n")
        zf.writestr(ip(md5sum_optional_fname), "\n".join("%s  %s" % t for t in md5sums_optional) + "\n")
        zf.writestr(
            ip("OPTIONAL.txt"),
            str_crlf(
                OPTIONAL_NOTE.format()
            ),
        )

    for org in organizations:
        zf.writestr(
            ip(
                "organization_metadata/organization_metadata_{}.csv".format(org["name"])
            ),
            org_with_extras_to_csv(org),
        )

    for typ, typ_packages in list(objects_by_attr(packages, "type", "unknown").items()):
        # some objects may not have a ckanext-scheming schema
        if typ is None:
            continue
        zf.writestr(
            ip("package_metadata/package_metadata_{}_{}.csv".format(pfx, typ)),
            schema_to_csv(typ, "dataset_fields", typ_packages),
        )

    for typ, typ_resources in list(objects_by_attr(
        resources, "resource_type", "unknown"
    ).items()):
        # some objects may not have a ckanext-scheming schema
        if typ is None:
            continue
        zf.writestr(
            ip("resource_metadata/resource_metadata_{}_{}.csv".format(pfx, typ)),
            schema_to_csv(typ, "resource_fields", typ_resources),
        )

    write_script("download.sh", SH_TEMPLATE)
    write_script("download.ps1", POWERSHELL_TEMPLATE)
    write_script("download.py", PY_TEMPLATE)

    zf.writestr(
        ip("QUERY.txt"),
        str_crlf(
            QUERY_TEMPLATE.format(
                prefix=pfx,
                timestamp=get_timestamp(),
                title=title,
                user_page=user_page,
                url_count=len(urls),
                md5_count=len(md5sums),
                url_optional_count=len(urls_optional),
                md5_optional_count=len(md5sums_optional),
                query=query,
                query_url=query_url,
                download_url=download_url,
                organization_count=organization_count,
                package_count=package_count,
                resource_count=resource_count,
                shared_files_count=shared_files_count,
                total_size=bitmath.Byte(bytes=total_size_bytes).best_prefix().format("{value:.2f} {unit}"),
                total_size_bytes=total_size_bytes,
            )
        ),
    )

    zf.writestr(
        ip("MEMBERSHIPS.txt"),
        str_crlf(
            generate_memberships_information(
                prefix=pfx,
                timestamp=get_timestamp(),
                title=title,
                user_page=user_page,
                organization_count=organization_count,
                memberships=memberships,
                access_required=access_required,
            )
        ),
    )

    zf.close()
    content = fd.getvalue()
    return make_response((content, 200, headers))
