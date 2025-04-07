# Get the password from input
$pw = Read-Host -Prompt "Enter the password" -AsSecureString
# Convert the password to plain text
$pw = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($pw))

# Get all CSV files in the data directory
Get-ChildItem -Path "../data/opentargets/target-association-scores/*.csv" | ForEach-Object {
    # Check if the file is not in the exclude list
    if (Test-Path $_.FullName -PathType Leaf) {
        Write-Host "Processing file: $($_.Name)"
        pnpm gos -f $_.FullName -u neo4j -p "$pw" -d "tbep" -U "bolt://localhost:7687" --nh
    }
}