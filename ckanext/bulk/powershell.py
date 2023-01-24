POWERSHELL_TEMPLATE = """\
#!/usr/bin/env pwsh

$env:CKAN_API_TOKEN=""
{% if user_page %}
$apikey = $Env:CKAN_API_KEY
$apitoken = $Env:CKAN_API_TOKEN
if (!$apikey && !$apitoken) {
  'Please set the CKAN_API_TOKEN environment variable.'
  ''
  'You can create your API Token by browsing to:'
  '{{ user_page }}'
  ''
  'The API key which has the format:'
  'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
  'is now obsolete, and you should create and use the'
  'API token insted. '
  ''
  'To set the environment variable in Linux/MacOS/Unix, use:'
  'export CKAN_API_TOKEN=**********************************'
  ''
  'On Microsoft Windows, within Powershell, use:'
  '$env:CKAN_API_TOKEN="******************************"'
  exit 1
}
{% else %}
$apikey = $null;
$apitoken = $null;
{% endif %}

#
# This PowerShell script was automatically generated.
#

function DownloadURL($url)
{
    $filename = $url.Substring($url.lastIndexOf('/') + 1)
    if (Test-Path $filename) {
        "File already exists, skipping download: " + $filename
        return
    }
    $client = new-object System.Net.WebClient
    if ($apitoken) {
        $client.Headers.Add('Authorization: ' + $apitokeny)
    } else {
        if ($apikey) {
            $client.Headers.Add('Authorization: ' + $apikey)
        }
    }   
    
    "Downloading: " + $filename
    $client.DownloadFile($url, $filename)
}

function VerifyMD5([String]$filename, [String]$expected_md5)
{
    $md5hash = new-object -TypeName System.Security.Cryptography.MD5CryptoServiceProvider
    try {
        $file = [System.IO.File]::Open($filename,[System.IO.Filemode]::Open, [System.IO.FileAccess]::Read)
        try {
            $actual_md5 = [System.BitConverter]::ToString($md5hash.ComputeHash($file)).Replace('-', '').toLower()
        } finally {
            $file.Dispose()
        }
    } catch [System.IO.FileNotFoundException] {
        $filename + ": FAILED open or read"
        return
    }
    if ($actual_md5 -eq $expected_md5) {
        $filename + ": OK"
    } else {
        $filename + ": FAILED"
    }
}


'Commencing bulk download of data from CKAN:'
''

$urls = Get-Content '{{ urls_fname }}'
ForEach ($line in $urls) {
    DownloadURL $line
}

'File downloads complete.'
''
'Verifying file checksums:'
''
$md5s = Get-Content '{{ md5sum_fname }}'
ForEach ($line in $md5s) {
    $md5, $filename = $line.Split(" ",[StringSplitOptions]'RemoveEmptyEntries')
    VerifyMD5 $filename $md5
}

"""
