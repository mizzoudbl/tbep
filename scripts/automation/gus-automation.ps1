# Define files to exclude
$excludeFiles = @(
    "ppi_db_string.csv",
    "funppi_db_string.csv",
    "intact_score.csv",
    "biogrid_score.csv",
    "hgnc_master_gene_list_with_uniprot.csv"
)

# Get the password from input
$pw = Read-Host -Prompt "Enter the password" -AsSecureString
# Convert the password to plain text
$pw = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($pw))

# Get all CSV files in the data directory
Get-ChildItem -Path "../data/*.csv" -Recurse | ForEach-Object {
    if ($excludeFiles -notcontains $_.Name -and (Test-Path $_.FullName -PathType Leaf) -and $_.Name -notmatch "^transformed_association_") {
        Write-Host "Processing file: $($_.Name)"
        pnpm gus -f $_.FullName -u neo4j -p "$pw" -d "tbep" -U "bolt://localhost:7687" --nh
    }
}