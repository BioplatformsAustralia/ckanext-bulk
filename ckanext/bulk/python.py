PY_TEMPLATE = '''\
#!/usr/bin/env python3

# download.py
# Bulk download tool for the Bioplatforms Australia Data Portal
#
# This Python script was automatically generated.

# Copyright 2021 Bioplatforms Australia

# License - GNU Affero General Public License v3.0
# https://github.com/BioplatformsAustralia/ckanext-bulk/blob/master/LICENSE.txt

# This script should be cross platform and work on Linux, Windows and MacOS

# Automatically generated variables
bpa_dltool_slug = "{{ prefix }}"
bpa_username = "{{ username }}"

# Static constants
user_agent = "data.bioplatforms.com download.py/0.4 (Contact help@bioplatforms.com)"

# All imports should be from the base python
import sys
import platform
import os
import hashlib
import logging

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
    block_size = 1024 * md5_object.block_size

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
    file_size = int(resGet.headers["Content-length"])
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


def download(api, source, target):
    # Downloads the whole file
    # Returns the local filename if succesful, else None
    logger.info("Downloading")
    headers = requests.utils.default_headers()
    headers.update({"User-Agent": user_agent, "Authorization": api})

    try:
        with requests.get(source, stream=True, headers=headers) as r:
            r.raise_for_status()
            with open(target, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except requests.exceptions.HTTPError as exception:
        logger.error("Failed download")
        logger.error(exception)
        return None
    return target


def check_for_api_key():
    # Check for CKAN API Key in the users environment
    # Returns the API Key if found, aborts otherwise

    api_key_message = """\
    Please set the CKAN_API_KEY environment variable.
    
{% if user_page %}
    You can find your API Key by browsing to:
        {{ user_page }}
    
    It will be in the bottom left hand corner of the web page.
    
{% endif %}
    The API key has the format:
        xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    """

    nix_instructions = """\
    To set the environment variable in Linux/MacOS/Unix, use
    the following command before running download.sh
    substituting your API key as required:
    
    export CKAN_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    
    You can check if it has been set correctly with the command:
    
    printenv CKAN_API_KEY
    """

    win_instructions = """\
    On Microsoft Windows, within Powershell, use:
    $env:CKAN_API_KEY="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    
    On Microsoft Windows, within a Command shell, use:
    set CKAN_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    
    You can check if it has been set correctly with the commands:
    
    dir env:  (for Powershell)
    set       (for a Command shell)
    """

    api_key = os.environ.get("CKAN_API_KEY")

    if not api_key:
        logger.warning("No API key set")
        print(api_key_message)
        if "Windows" in platform.platform():
            print(win_instructions)
        else:
            print(nix_instructions)
        sys.exit(1)

    logger.info("API key found")
    logger.info("Platform: %s" % platform.platform())

    return api_key


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


def log_file_when_present(filename,description):
    if not (os.path.isfile(filename) and os.access(filename, os.R_OK)):
       return
    logger.info("%s found" % (description,))
    with open(filename, "r") as logfh:
        for line in logfh.readlines():
            logger.info(line.rstrip())
    logger.info("END %s" % (description,))


def main():
    logger.info(user_agent)
    logger.info("Download Tool slug: %s" % bpa_dltool_slug)
    logger.info("BPA Portal Username: %s" % bpa_username)

    api_key = check_for_api_key()

    # Check for our list of URLs and MD5 values
    script_dir = os.path.dirname(os.path.abspath(__file__))
    url_list = f"{script_dir}{os.path.sep}tmp{os.path.sep}{bpa_dltool_slug}_urls.txt"
    md5_file = f"{script_dir}{os.path.sep}tmp{os.path.sep}{bpa_dltool_slug}_md5sum.txt"
    query_file = f"{script_dir}{os.path.sep}QUERY.txt"

    # Add QUERY.txt to debug output
    log_file_when_present(query_file, "QUERY.txt")

    # Check we are being run from a suitable location

    file_present(url_list, "URL list")
    file_present(md5_file, "MD5 file")

    # TODO: Add argument parsing to enable runtime setting of
    # download location, debug level, API Key

    process_downloads(api_key, url_list, md5_file, script_dir)

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
            logger.info("       File: %d/%d" % (counts["processed"], len(md5)))
            logger.info("Downloading: %s" % (filename,))
            logger.info("       from: %s" % (url,))
            logger.info("         to: %s" % (dl_path,))

            valid = False

            if not (os.path.isfile(dl_path) and os.access(dl_path, os.R_OK)):
                #    If file not present,
                #        begin download
                #        Check MD5 sum
                #        Log errors
                logger.info("File %s - not present, downloading..." % (filename,))
                counts["fresh"] += 1
                if download(api_key, url, dl_path):
                    valid = check_md5sum(dl_path, md5[filename])
                else:
                    valid = False
                if valid:
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
                    counts["noremotesize"] += 1
                    valid = check_md5sum(dl_path, md5[filename])
                    if valid:
                        counts["valid"] += 1
                        print(filename)
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
                        print(filename)
                    else:
                        counts["invalid"] += 1
                        counts["rerun"] += 1
                if local == remote:
                    valid = check_md5sum(dl_path, md5[filename])
                    if valid:
                        logger.info("File already downloaded")
                        counts["valid"] += 1
                        print(filename)
                        continue
                    else:
                        logger.info(
                            "File corrupted, same size but failed checksum, attempting to redownload..."
                        )
                        counts["corrupted"] += 1
                        os.remove(dl_path)
                    counts["redownload"] += 1
                    if download(api_key, url, dl_path):
                        valid = check_md5sum(dl_path, md5[filename])
                    else:
                        valid = False
                    if valid:
                        counts["valid"] += 1
                        print(filename)
                    else:
                        counts["invalid"] += 1
                if local > remote:
                    logger.info(
                        "File corrupted, larger than remote, attempting to redownload..."
                    )
                    counts["corrupted"] += 1
                    os.remove(dl_path)
                    counts["redownload"] += 1
                    if download(api_key, url, dl_path):
                        valid = check_md5sum(dl_path, md5[filename])
                    else:
                        valid = False
                    if valid:
                        counts["valid"] += 1
                        print(filename)
                    else:
                        counts["invalid"] += 1

    # Summary after all files/URLs processed
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
