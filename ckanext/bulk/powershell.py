POWERSHELL_TEMPLATE = """\
#!/usr/bin/env pwsh

{% if user_page %}
param(
    [Parameter(HelpMessage="Download optional files")]
    [Alias("o")]
    [switch]$Optional = $False
)

$user_agent = "data.bioplatforms.com download.ps1/0.4 (Contact help@bioplatforms.com)"

$apikey = $Env:CKAN_API_KEY
$apitoken = $Env:CKAN_API_TOKEN

if ($apikey -and !$apitoken) {
  'Migrate from CKAN_API_KEY to CKAN_API_TOKEN'
  ''
  'The API key which has the format:'
  'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
  'is now obsolete, and you should create and use the'
  'API token instead. '
  ''
}

if (!$apitoken) {
  'Please set the CKAN_API_TOKEN environment variable.'
  ''
  'You can create your API Token by browsing to:'
  '{{ user_page }}'
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
    $filename_only = $url.Substring($url.lastIndexOf('/') + 1)
    $filename = ($PSScriptRoot + '/' + $filename_only)

    if (Test-Path $filename) {
        "File already exists, skipping download: " + $filename
        return
    }
    $client = new-object System.Net.WebClient
    $client.Headers.add("user-agent", $user_agent)
    if ($apitoken) {
        $client.Headers.Add('Authorization: ' + $apitoken)
    } else {
        if ($apikey) {
            $client.Headers.Add('Authorization: ' + $apikey)
        }
    }   
    
    "Downloading: " + $filename_only
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

# Output information files

function DisplayFile([String]$filename, [String]$description) {
    '------------------------------------------------------------------------'
    $description
    '------------------------------------------------------------------------'
    Get-Content $filename |ForEach-Object {"    $_"}
}

DisplayFile .\README.txt 'README.txt'
DisplayFile .\MEMBERSHIPS.txt 'MEMBERSHIPS.txt'
if([System.IO.File]::Exists('.\OPTIONAL.txt')){
    DisplayFile .\OPTIONAL.txt 'OPTIONAL.txt'
}


# Force downloads to location where script is
Set-Location -Path $PSScriptRoot

function DownloadData([String]$urlfile, [String]$md5file, [String]$annotation) {
    ''
    '------------------------------------------------------------------------'
    'Commencing bulk download of data from CKAN (' + $annotation + ') : '
    '------------------------------------------------------------------------'
    ''

    $urls = Get-Content  ($PSScriptRoot + '/' + $urlfile)
    ForEach ($line in $urls) {
        DownloadURL $line
    }

    'File downloads complete.'
    ''
    'Verifying file checksums:'
    ''
    $md5s = Get-Content ($PSScriptRoot + '/' + $md5file)
    ForEach ($line in $md5s) {
        $md5, $filename = $line.Split(" ",[StringSplitOptions]'RemoveEmptyEntries')
        VerifyMD5 $filename $md5
    }
}

function CheckFileStatus {
    param(
        [Parameter(
            Mandatory=$True,
            ValueFromRemainingArguments=$true,
            Position = 0
        )][string[]]
        $fileArgs
    )

    foreach($fileArg in $fileArgs) {
        try {
            if(! [System.IO.File]::Exists($PSScriptRoot + '/' + $fileArg)){
                return $False
            }

            [System.IO.File]::OpenRead($PSScriptRoot + '/' + $fileArg).Close()
        }
        catch {
            return $False
        }
    }

    return $True
}

DownloadData '{{ urls_fname }}' '{{ md5sum_fname }}' 'main'

if($Optional -and (CheckFileStatus '{{ urls_optional_fname }}' '{{ md5sum_optional_fname }}')) {
    DownloadData '{{ urls_optional_fname }}' '{{ md5sum_optional_fname }}' 'optional'
}
"""
