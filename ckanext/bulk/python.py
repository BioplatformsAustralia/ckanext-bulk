PY_TEMPLATE = '''\
#!/usr/bin/env python3

# download.py
# Bulk download tool for the Bioplatforms Australia Data Portal
#
# This Python script was automatically generated.

# Copyright 2023 Bioplatforms Australia

# License - GNU Affero General Public License v3.0
# https://github.com/BioplatformsAustralia/ckanext-bulk/blob/master/LICENSE.txt

# This script should be cross platform and work on Linux, Windows and MacOS

# Automatically generated variables
bpa_dltool_slug = "{{ prefix }}"
bpa_username = "{{ username }}"

# Static constants
user_agent = "data.bioplatforms.com download.py/0.9 {{ username }} (Contact help@bioplatforms.com)"

# All imports should be from the base python
import sys
import platform
import os
import hashlib
import logging
import argparse
from urllib.parse import urlparse

if __name__ == "__main__":
    # Unfortunately, we need requests
    # If not present, output instructions
    try:
        import requests
    except ImportError:
        print("We need the requests module to function")
        print()
        print("Install using the following command:")
        print("    python3 -m pip install requests")
        sys.exit(4)

    # Complain if we are not running Python 3.4 or later

    if not sys.version_info >= (3, 4):
        print("Your python version appears to be too old.")
        print("A minimum of 3.4 is required.")
        print()
        print("Please upgrade.")
        sys.exit(3)
else:
    import requests


def make_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(level)
    handler = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s [%(levelname)-7s] [%(name)s]  %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger


def check_md5sum(fullpath, checksum):
    # Returns true if file matches checksum
    filename = fullpath.split(os.path.sep)[-1]

    md5_object = hashlib.md5()
    block_size = 64 * 1024 * md5_object.block_size

    f = open(fullpath, "rb")
    chunk = f.read(block_size)
    while chunk:
        # md5_object.update(bytearray(chunk))
        md5_object.update(chunk)
        chunk = f.read(block_size)

    md5_hash = md5_object.hexdigest()

    if md5_hash == checksum:
        logger.info(f"VALID checksum for {filename} matches {checksum}")
    else:
        logger.warning(f"FAILED checksum for {filename} does not match {checksum}")

    return md5_hash == checksum


def get_remote_file_size(api, url):
    # This method returns None if it is not able to determine
    # the remote file size
    headers = requests.utils.default_headers()
    headers.update({"User-Agent": user_agent, "Authorization": api})

    resGet = requests.get(url, stream=True, headers=headers)
    contentLength = resGet.headers.get("Content-length")
    if contentLength is None:
        u = urlparse(resGet.url)
        if u.path == "/user/login":
            logger.warning(
                "Potential CKAN_API_TOKEN issue or insufficient access to requested resource"
            )
        else:
            logger.warning("Unknown error")
            logger.warning(u.path)
        logger.warning(
            "First try to rerun this script, and if the problem persists, consult the documentation at https://usersupport.bioplatforms.com/programmatic_access.html."
        )
        logger.warning(
            "If your issue is still unresolved, please email QUERY.txt, MEMBERSHIPS.txt files and output to help@bioplatforms.com for support"
        )
        return None
    file_size = int(contentLength)
    return file_size


def resume_download(api, source, target):
    # Resumes the download based on the present size of the target
    # Returns the local filename if succesful, else None
    have = os.path.getsize(target)

    logger.info("Resuming download at: %d" % have)

    headers = requests.utils.default_headers()
    headers.update(
        {"User-Agent": user_agent, "Authorization": api, "Range": "bytes=%d-" % have}
    )

    try:
        with requests.get(
            source, stream=True, headers=headers, allow_redirects=True
        ) as r:
            r.raise_for_status()
            # append
            with open(target, "ab") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except requests.exceptions.HTTPError as exception:
        logger.error("Failed (re)-download")
        logger.error(exception)
        return None
    return target


def download(api, source, target, checksum=None):
    # Downloads the whole file
    # Returns the local filename if succesful, else None
    # If checksum provided, calculate it on the fly
    logger.info("Downloading")
    headers = requests.utils.default_headers()
    headers.update({"User-Agent": user_agent, "Authorization": api})

    md5_object = hashlib.md5()

    try:
        with requests.get(
            source, stream=True, headers=headers, allow_redirects=True
        ) as r:
            r.raise_for_status()
            with open(target, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if checksum is not None:
                        md5_object.update(chunk)
                    f.write(chunk)
    except requests.exceptions.HTTPError as exception:
        logger.error("Failed download")
        logger.error(exception)
        return None

    if checksum is not None:
        # Returns true if file matches checksum
        md5_hash = md5_object.hexdigest()

        if md5_hash == checksum:
            logger.info(f"VALID checksum for {target} matches {checksum}")
        else:
            logger.warning(f"FAILED checksum for {target} does not match {checksum}")
            return None

    return target


def check_for_api_key():
    # Check for CKAN API Key or token in the users environment
    # Returns the API Token first,or the Key if found, aborts otherwise

    api_key_message = """\
    Please set the CKAN_API_TOKEN environment variable.
    
{% if user_page %}
    You can generate your API Token by browsing to:
        {{ user_page }}
    
    Go to the API Tokens tab, and generate your token.
    
{% endif %}
    The API key of the format:
        xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    is now obsolete, and should be replaced wih a freshly
    generated API Token.
    """

    nix_instructions = """\
    To set the environment variable in Linux/MacOS/Unix, use
    the following command before running download.sh
    substituting your API key as required:
    
    export CKAN_API_TOKEN=************************************
    
    You can check if it has been set correctly with the command:
    
    printenv CKAN_API_TOKEN
    """

    win_instructions = """\
    On Microsoft Windows, within Powershell, use:
    $env:CKAN_API_TOKEN="**************************************"
    
    On Microsoft Windows, within a Command shell, use:
    set CKAN_API_TOKEN=***************************************
    
    You can check if it has been set correctly with the commands:
    
    dir env:  (for Powershell)
    set       (for a Command shell)
    """

    api = ""
    api_token = os.environ.get("CKAN_API_TOKEN")

    if not api_token:
        logger.warning("No API token set, trying obsolete API key")
        api_key = os.environ.get("CKAN_API_KEY")

        if not api_key:
            logger.warning("No API token OR key set")
            print(api_key_message)
            if "Windows" in platform.platform():
                print(win_instructions)
            else:
                print(nix_instructions)
            sys.exit(1)
        else:
            logger.info("API key found")
            api = api_key

    else:
        logger.info("API token found")
        api = api_token
    logger.info("Platform: %s" % platform.platform())

    return api


def file_present(filename, description):
    # Check if file present in download tool archive
    # Aborts otherwise
    if not (os.path.isfile(filename) and os.access(filename, os.R_OK)):
        logger.error("%s not found or unreadable" % (filename,))
        error_message = """\
%s not found

%s can not be accessed
Please check directory and file exists
""" % (
            filename,
            description,
        )
        print(error_message)
        sys.exit(1)
    logger.info("%s found" % (description,))


def check_files(*filelist):
    for filename in filelist:
        if not (os.path.isfile(filename) and os.access(filename, os.R_OK)):
            return False
    return True


def log_file_when_present(filename,description):
    if not (os.path.isfile(filename) and os.access(filename, os.R_OK)):
       return
    logger.info("%s found" % (description,))
    with open(filename, "r") as logfh:
        for line in logfh.readlines():
            logger.info(line.rstrip())
    logger.info("END %s" % (description,))


def main():
    description = (
        """
        %s

        Tool to download files from the Bioplatforms Australia Data Portal
        """
        % (user_agent,)
    )
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description=description
    )
    parser.add_argument(
        "-o", "--optional", action="store_true", help="Download optional files"
    )
    parsed = parser.parse_args()

    logger.info(user_agent)
    logger.info("Download Tool slug: %s" % bpa_dltool_slug)
    logger.info("BPA Portal Username: %s" % bpa_username)

    api_key = check_for_api_key()

    # Check for our list of URLs and MD5 values
    script_dir = os.path.dirname(os.path.abspath(__file__))
    url_list = f"{script_dir}{os.path.sep}tmp{os.path.sep}{bpa_dltool_slug}_urls.txt"
    md5_file = f"{script_dir}{os.path.sep}tmp{os.path.sep}{bpa_dltool_slug}_md5sum.txt"
    url_optional_list = (
        f"{script_dir}{os.path.sep}tmp{os.path.sep}{bpa_dltool_slug}_urls_optional.txt"
    )
    md5_optional_file = f"{script_dir}{os.path.sep}tmp{os.path.sep}{bpa_dltool_slug}_md5sum_optional.txt"
    query_file = f"{script_dir}{os.path.sep}QUERY.txt"
    memberships_file = f"{script_dir}{os.path.sep}MEMBERSHIPS.txt"
    optional_file = f"{script_dir}{os.path.sep}OPTIONAL.txt"

    # Add QUERY.txt to debug output
    log_file_when_present(query_file, "QUERY.txt")

    # Add MEMBERSHIPS.txt to debug output
    log_file_when_present(memberships_file, "MEMBERSHIPS.txt")

    # Add OPTIONAL.txt to debug output
    log_file_when_present(optional_file, "OPTIONAL.txt")
    if parsed.optional and check_files(url_optional_list, md5_optional_file):
        logger.info("Will download OPTIONAL files")
        logger.info("Downloading main files first ...")
        logger.info("-----------")

    # Check we are being run from a suitable location

    file_present(url_list, "URL list")
    file_present(md5_file, "MD5 file")

    # TODO: Add argument parsing to enable runtime setting of
    # download location, debug level, API Key

    process_downloads(api_key, url_list, md5_file, script_dir)

    if parsed.optional and check_files(url_optional_list, md5_optional_file):
        logger.info("-----------")
        logger.info("Processing and downloading OPTIONAL files ...")
        logger.info("-----------")
        # Preflight checks
        file_present(url_optional_list, "URL optional list")
        file_present(md5_optional_file, "MD5 optional file")

        process_downloads(api_key, url_optional_list, md5_optional_file, script_dir)
    elif not parsed.optional and check_files(url_optional_list, md5_optional_file):
        logger.info("Skipping downloading OPTIONAL files")
    elif parsed.optional and not check_files(url_optional_list, md5_optional_file):
        logger.warning("OPTIONAL files not present")
        logger.warning("There may be file problems - email help@bioplatforms.com")


def process_downloads(api_key, url_list, md5_file, target_dir):
    # Open MD5 file and populate cache

    md5 = {}
    counts = {
        "valid": 0,
        "invalid": 0,
        "fresh": 0,
        "failed": 0,
        "present": 0,
        "corrupted": 0,
        "redownload": 0,
        "resume": 0,
        "rerun": 0,
        "processed": 0,
        "noremotesize": 0,
    }

    with open(md5_file, "r") as md5fh:
        for line in md5fh.readlines():
            try:
                (checksum, filename) = line.strip().split("  ", 1)
                md5[filename] = checksum
            except ValueError as exception:
                logger.error("Failed to parse MD5 line")
                logger.error("Line     : %s" % (line,))
                logger.error("Exception: %s" % (exception,))

    # Open list of URLs

    logger.info("%d files to download" % (len(md5),))
    logger.info("Manifest: %s" % (url_list,))

    # For each URL
    with open(url_list, "r") as urlfh:
        for url in urlfh.readlines():
            url = url.strip()
            filename = url.strip().split("/")[-1]
            dl_path = f"{target_dir}{os.path.sep}{filename}"

            # Find MD5 sum for file
            if not filename in md5:
                logging.error("No MD5 sum found for %s" % (filename,))
                sys.exit(2)

            counts["processed"] += 1
            logger.info("-----------")
            logger.info("       File: %d/%d" % (counts["processed"], len(md5)))
            logger.info("Downloading: %s" % (filename,))
            logger.info("       from: %s" % (url,))
            logger.info("         to: %s" % (dl_path,))

            valid = False

            if not (os.path.isfile(dl_path) and os.access(dl_path, os.R_OK)):
                #    If file not present,
                #        Check file size on mirror, note error, skip
                #        begin download
                #        Check MD5 sum
                #        Log errors
                logger.info("Checking file size and access...")
                remote = get_remote_file_size(api_key, url)
                if remote is None:
                    logger.warning("Remote file size could not determined, skipping")
                    counts["noremotesize"] += 1
                    counts["failed"] += 1
                    continue
                logger.info("File %s - not present, downloading..." % (filename,))
                counts["fresh"] += 1
                if download(api_key, url, dl_path, md5[filename]):
                    counts["valid"] += 1
                else:
                    # assume transfer failed, keep the file around
                    counts["failed"] += 1
            else:
                #    If file present,
                #        Check file size on mirror
                #          If no, file size, check md5 / skip
                #        If less than file size,
                #          resume download
                #        Log errors
                #          Check MD5 sum
                #          Log errors
                #        If equal size,
                #          Check MD5 Sum
                #          If valid, move onto next URL, else delete
                #          Begin download
                #          Check MD5 sum
                #        If greater size,
                #          Delete file
                #          begin download
                #          Check MD5 sum
                #          Log errors
                counts["present"] += 1
                logger.info("File %s - present, checking integrity..." % (filename,))
                local = os.path.getsize(dl_path)
                remote = get_remote_file_size(api_key, url)
                if remote is None:
                    logger.warning("Remote file size could not determined")
                    logger.info("Checking file integrity anyhow...")
                    counts["noremotesize"] += 1
                    valid = check_md5sum(dl_path, md5[filename])
                    if valid:
                        counts["valid"] += 1
                        logger.info("%s valid" % (filename,))
                    else:
                        counts["invalid"] += 1
                    continue

                # Compare file sizes

                if local < remote:
                    # assume interrupted as opposed to corrupt
                    logger.info("Resuming download due to partial file...")
                    counts["resume"] += 1
                    if resume_download(api_key, url, dl_path):
                        valid = check_md5sum(dl_path, md5[filename])
                    else:
                        valid = False
                    if valid:
                        counts["valid"] += 1
                    else:
                        counts["invalid"] += 1
                        counts["rerun"] += 1
                if local == remote:
                    valid = check_md5sum(dl_path, md5[filename])
                    if valid:
                        logger.info("File already downloaded")
                        counts["valid"] += 1
                        continue
                    else:
                        logger.info(
                            "File corrupted, same size but failed checksum, attempting to redownload..."
                        )
                        counts["corrupted"] += 1
                        os.remove(dl_path)
                    counts["redownload"] += 1
                    if download(api_key, url, dl_path, md5[filename]):
                        counts["valid"] += 1
                    else:
                        counts["invalid"] += 1
                if local > remote:
                    logger.info(
                        "File corrupted, larger than remote, attempting to redownload..."
                    )
                    counts["corrupted"] += 1
                    os.remove(dl_path)
                    counts["redownload"] += 1
                    if download(api_key, url, dl_path, md5[filename]):
                        counts["valid"] += 1
                    else:
                        counts["invalid"] += 1

    # Summary after all files/URLs processed
    logger.info("-----------")
    logger.info("Session summary: %s" % (str(counts),))

    if counts["valid"] == len(md5):
        logger.info("All files sucessfully downloaded.")
    else:
        if counts["failed"] > 0:
            logger.warning(
                "%d failed downloads, re-run to attempt to fix" % (counts["failed"],)
            )

        if counts["rerun"] > 0:
            logger.warning(
                "%d corrupted files after resumed download, re-run to attempt to fix"
                % (counts["rerun"],)
            )

        if counts["invalid"] > 0:
            logger.warning(
                "%d corrupted files, re-run to attempt to fix" % (counts["invalid"],)
            )


logger = make_logger(__name__)

if __name__ == "__main__":
    # execute only if run as a script
    main()
'''
