SH_TEMPLATE = '''\
#!/bin/sh

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

if ! which wget >/dev/null 2>&1; then
  echo "`wget` is not installed. Please install it."
  echo
  echo "On MacOS, it can be installed via HomeBrew (https://brew.sh/)"
  echo "using the command `brew install wget`"
  exit 1
fi

echo "Downloading data"
if [ x"$CKAN_API_KEY" = "x" ]; then
    wget -c -t 0 -i urls.txt
else
    wget --header="Authorization: $CKAN_API_KEY" -c -t 0 -i urls.txt
fi

echo "Data download complete. Verifying checksums:"
md5sum -c md5sum.txt 2>&1 | tee md5sum.log
'''
