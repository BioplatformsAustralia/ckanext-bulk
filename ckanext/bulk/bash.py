SH_TEMPLATE = """\
#!/bin/bash

#
# This UNIX shell script was automatically generated.
#
{% if user_page %}
if [ x"$CKAN_API_KEY" = "x" ]; then
  echo "Please set the CKAN_API_KEY environment variable."
  echo
  echo "You can find your API Key by browsing to:"
  echo "{{ user_page }}"
  echo
  echo "The API key has the format:"
  echo "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  echo
  echo "To set the environment variable in Linux/MacOS/Unix, use:"
  echo "export CKAN_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  echo ""
  exit 1
fi
{% endif %}

if ! which curl >/dev/null 2>&1; then
  echo "`curl` is not installed. Please install it."
  echo
  echo "On MacOS, it can be installed via HomeBrew (https://brew.sh/)"
  echo "using the command `brew install curl`"
  exit 1
fi

if ! which md5sum >/dev/null 2>&1; then
  echo "`md5sum` is not installed. Please install it."
  echo
  echo "On MacOS, it can be installed via HomeBrew (https://brew.sh/)"
  echo "using the command `brew install md5sha1sum`"
  exit 1
fi

echo "Downloading data"
while read URL; do
    echo "Downloading: $URL"
    curl -O -L -C - -H "Authorization: $CKAN_API_KEY" "$URL"
done < {{ urls_fname }}

echo "Data download complete. Verifying checksums:"
md5sum -c {{ md5sum_fname }} 2>&1 | tee tmp/md5sum.log
"""
