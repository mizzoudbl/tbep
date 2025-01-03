# Create result directory if it doesn't exist
New-Item -ItemType Directory -Path "result" -Force | Out-Null

# Store jobs in a hashtable for tracking
$jobs = @{}

# Store files to skip in an array
$skipFiles = @(
    "hgnc_master_gene_list_with_uniprot.csv", 
    "ppi_db_string.csv", 
    "funppi_db_string.csv"
)

try {
    # Get all CSV files in the data directory recursively
    Get-ChildItem -Filter "data/*.csv" -Recurse | ForEach-Object {
        if ($skipFiles -contains $_.Name) {
            Write-Host "Skipping file: $($_.Name)"
            return
        }
        
        $outputFile = "result/" + $_.BaseName + "-verified.csv"
        
        # Start background job
        $job = Start-Job -ScriptBlock {
            param($inputFile, $outputFile)
            & pnpm opp -i $inputFile -o $outputFile
            return "Completed processing: $inputFile"
        } -ArgumentList $_.FullName, $outputFile
        
        # Store job with file info
        $jobs[$job.Id] = $_.Name
        Write-Host "Started processing: $($_.Name) [Job ID: $($job.Id)]"
    }

    # Monitor jobs and handle completion
    while ($jobs.Count -gt 0) {
        $completed = Get-Job | Where-Object { $jobs.ContainsKey($_.Id) -and $_.State -eq "Completed" }
        foreach ($job in $completed) {
            # Get and display job output
            Receive-Job -Job $job | Write-Host
            
            # Clean up job
            Remove-Job -Job $job
            $jobs.Remove($job.Id)

            # Clear console
            Clear-Host
            
            # Display remaining jobs
            $jobsTable = @()
            $jobs.GetEnumerator() | ForEach-Object {
                $jobsTable += [PSCustomObject]@{
                    "Job ID" = $_.Key
                    "File" = $_.Value
                }
            }
            $jobsTable | Format-Table -AutoSize
        }
        Start-Sleep -Milliseconds 100
    }
} finally {
    # Clean up any remaining jobs when script exits
    Get-Job | Where-Object { $jobs.ContainsKey($_.Id) } | ForEach-Object {
        Write-Host "Cleaning up job $($_.Id)..."
        Stop-Job -Job $_ -ErrorAction SilentlyContinue
        Remove-Job -Job $_ -Force
    }
    $jobs.Clear()
}