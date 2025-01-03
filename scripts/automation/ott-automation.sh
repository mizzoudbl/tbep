#!/bin/bash

# Create result directory if it doesn't exist
mkdir -p result

# Store files to skip in an array
skipFiles=("hgnc_master_gene_list_with_uniprot.csv" "ppi_db_string.csv" "funppi_db_string.csv")

# Function to check if an element is in an array
containsElement () {
  local e match="$1"
  shift
  for e; do [[ "$e" == "$match" ]] && return 0; done
  return 1
}

# Store jobs in an associative array for tracking
declare -A jobs

# Get all CSV files in the data directory recursively
find data -type f -name "*.csv" | while read -r file; do
  filename=$(basename "$file")
  
  if containsElement "$filename" "${skipFiles[@]}"; then
    echo "Skipping file: $filename"
    continue
  fi
  
  outputFile="result/${filename%.csv}-verified.csv"
  
  # Start background job
  (
    pnpm opp -i "$file" -o "$outputFile"
    echo "Completed processing: $file"
  ) &
  
  jobId=$!
  jobs["$jobId"]="$filename"
  echo "Started processing: $filename [Job ID: $jobId]"
done

# Monitor jobs and handle completion
while [ ${#jobs[@]} -gt 0 ]; do
  for jobId in "${!jobs[@]}"; do
    if ! kill -0 "$jobId" 2>/dev/null; then
      wait "$jobId"
      echo "Completed processing: ${jobs[$jobId]}"
      unset jobs["$jobId"]
      
      # Clear console
      clear
      
      # Display remaining jobs
      echo "Remaining jobs:"
      for id in "${!jobs[@]}"; do
        echo "Job ID: $id, File: ${jobs[$id]}"
      done
    fi
  done
  sleep 0.1
done

# Clean up any remaining jobs when script exits
trap 'for jobId in "${!jobs[@]}"; do kill "$jobId" 2>/dev/null; done' EXIT
