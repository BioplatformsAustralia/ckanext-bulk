SH_TEMPLATE = """\
#!/bin/bash

# download.sh
# Bulk download tool for the Bioplatforms Australia Data Portal
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
  echo "It will be in the bottom left hand corner of the web page."
  echo
  echo "The API key has the format:"
  echo "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  echo
  echo "To set the environment variable in Linux/MacOS/Unix, use"
  echo "the following command before running download.sh"
  echo "substituting your API key as required:"
  echo
  echo "export CKAN_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  echo
  echo "You can check if it has been set correctly with the command:"
  echo
  echo "printenv CKAN_API_KEY"
  exit 1
fi
{% endif %}

# Check we are being run from a suitable location

if [ ! -f {{ urls_fname }} ]; then
  echo "{{ urls_fname }} not found"
  echo
  echo "Please change to the directory containing the download.sh script"
  exit 1
fi

# Check for required programs

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

BPA_AGENT="data.bioplatforms.com download.sh/1.0"

CURL=`which curl`

# if on MacOS, favour homebrew curl over system curl
case "$OSTYPE" in
  darwin*)
    HBCURL="/usr/local/opt/curl/bin/curl"
    if [ -f $HBCURL -a -x $HBCURL ] ; then
        echo "Using curl installed via homebrew"
        CURL="$HBCURL"
    fi
    ;;
  *)
    ;;
esac

# Check program versions

# 7.58 required for correct Authorization header support
CURL_VERSION_REQUIRED="7.58"
CURL_VERSION=$($CURL --version | head -1 | awk '{print $2}')

function max()
{
  local m="$1"
  for n in "$@"
  do
    [ "$n" -gt "$m" ] && m="$n"
  done
  echo "$m"
}

# from https://apple.stackexchange.com/a/261863
function compare_versions()
{
  local v1=( $(echo "$1" | tr '.' ' ') )
  local v2=( $(echo "$2" | tr '.' ' ') )
  {# quoting to get around jinja templating comment #}
  local len="$(max "${{ '{#' }}v1[*]}" "${{ '{#' }}v2[*]}")"
  for ((i=0; i<len; i++))
  do
    [ "${v1[i]:-0}" -gt "${v2[i]:-0}" ] && return 1
    [ "${v1[i]:-0}" -lt "${v2[i]:-0}" ] && return 2
  done
  return 0
}

compare_versions $CURL_VERSION $CURL_VERSION_REQUIRED
if [ $? -eq 2 ]; then
  echo "Your 'curl' version is outdated."
  echo
  echo "Path was                   : $CURL"
  echo
  echo "Minimum version required is: $CURL_VERSION_REQUIRED"
  echo "Version available is       : $CURL_VERSION"
  exit 1
fi

# Undertake download

echo "Downloading data"
while read URL; do
  echo "Downloading: $URL"
  $CURL -O -L -C - -A "$BPA_AGENT" -H "Authorization: $CKAN_API_KEY" "$URL"
  if [ $? -ne 0 ] ; then
     echo "Error downloading: $URL"
  fi
done < {{ urls_fname }}

echo "Data download complete. Verifying checksums:"
md5sum -c {{ md5sum_fname }} 2>&1 | tee tmp/md5sum.log
"""
