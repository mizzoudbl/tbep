###########################################################################
# Ids of the parquet file changes with new version of Open Targets
# Just verify the parquet file names in the ftp server and edit accordingly
###########################################################################

# Maximum number of concurrent jobs
$MAX_JOBS = 20

# Create directories with parent directories if they don't exist
New-Item -Path "../data/overall" -ItemType Directory -Force

# Base URL
$BASE_URL = "ftp://ftp.ebi.ac.uk/pub/databases/opentargets/platform/latest/output/association_overall_direct"

# Array to hold jobs
$jobs = @()

# Download overall association scores
for ($i = 0; $i -lt 200; $i++) {
    $paddedNumber = "{0:00000}" -f $i
    
    # Start a background job
    $job = Start-Job -ScriptBlock {
        param($paddedNumber, $BASE_URL)
        Write-Output "Downloading part-$paddedNumber..."
        Invoke-WebRequest -Uri "$BASE_URL/part-$paddedNumber-67ea6339-0087-4bca-bb51-0de521275806-c000.snappy.parquet" -OutFile "../data/overall/part-$paddedNumber-67ea6339-0087-4bca-bb51-0de521275806-c000.snappy.parquet"
        Write-Output "Finished part-$paddedNumber"
    } -ArgumentList $paddedNumber, $BASE_URL
    
    $jobs += $job
    
    # If we reach the max job limit, wait for one to complete
    if ($jobs.Count -ge $MAX_JOBS) {
        $completedJob = $jobs | Wait-Job -Any
        $completedJob | Receive-Job
        $completedJob | Remove-Job
        $jobs = @($jobs | Where-Object { $_.State -ne "Completed" })
    }
}

# Wait for remaining jobs to complete
$jobs | Wait-Job | Receive-Job
$jobs | Remove-Job

Write-Output "Downloading Overall Association Score completed."

# Create data-source directory
New-Item -Path "../data/data-source" -ItemType Directory -Force

# Base URL for data source
$BASE_URL = "ftp://ftp.ebi.ac.uk/pub/databases/opentargets/platform/latest/output/association_by_datasource_direct"

# Clear jobs array
$jobs = @()

# Download data source association scores
for ($i = 0; $i -lt 200; $i++) {
    $paddedNumber = "{0:00000}" -f $i
    
    # Start a background job
    $job = Start-Job -ScriptBlock {
        param($paddedNumber, $BASE_URL)
        Write-Output "Downloading part-$paddedNumber..."
        Invoke-WebRequest -Uri "$BASE_URL/part-$paddedNumber-ff24ab98-2b98-48d9-a85b-f94f710232ea-c000.snappy.parquet" -OutFile "../data/data-source/part-$paddedNumber-ff24ab98-2b98-48d9-a85b-f94f710232ea-c000.snappy.parquet"
        Write-Output "Finished part-$paddedNumber"
    } -ArgumentList $paddedNumber, $BASE_URL
    
    $jobs += $job
    
    # If we reach the max job limit, wait for one to complete
    if ($jobs.Count -ge $MAX_JOBS) {
        $completedJob = $jobs | Wait-Job -Any
        $completedJob | Receive-Job
        $completedJob | Remove-Job
        $jobs = @($jobs | Where-Object { $_.State -ne "Completed" })
    }
}

# Wait for remaining jobs to complete
$jobs | Wait-Job | Receive-Job
$jobs | Remove-Job

Write-Output "Downloading Association by DataSource Score completed."


python ../ot-association-preprocessing.py

node ../gene-opentargets-disease-association-seed.js -f ../data/ot_overall_association_score.csv -U bolt://localhost:7687 -u neo4j -d tbep
node ../gene-opentargets-disease-association-seed.js -f ../data/ot_datasource_association_score.csv -U bolt://localhost:7687 -u neo4j -d tbep