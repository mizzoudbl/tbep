#!/bin/bash


###########################################################################
# Ids of the parquet file changes with new version of Open Targets
# Just verify the parquet file names in the ftp server and edit accordingly
###########################################################################

# Maximum number of concurrent jobs
MAX_JOBS=20

mkdir -p ../data/overall

# Base URL
BASE_URL="ftp://ftp.ebi.ac.uk/pub/databases/opentargets/platform/latest/output/association_overall_direct"
fileID=$(curl -s $BASE_URL | tail -n 1 | grep -oE 'part-[0-9]{5}-[^"]+\.parquet' | head -n 1 | cut -c12-)
# Job counter
job_count=0

for i in $(seq -f '%05g' 0 199); do
    (
        echo "Downloading part-$i..."
        wget -q -P ../data/overall "${BASE_URL}/part-$i-$fileID"
        echo "Finished part-$i"
    ) &

    # Increase job count and check if we hit the limit
    ((job_count++))
    if ((job_count >= MAX_JOBS)); then
        wait
        job_count=0
    fi
done

echo "Downloading Overall Association Score completed."

mkdir -p ../data/data-source
# Base URL
BASE_URL="ftp://ftp.ebi.ac.uk/pub/databases/opentargets/platform/latest/output/association_by_datasource_direct"
fileID=$(curl -s $BASE_URL | tail -n 1 | grep -oE 'part-[0-9]{5}-[^"]+\.parquet' | head -n 1 | cut -c12-)
# Job counter
job_count=0

for i in $(seq -f '%05g' 0 199); do
    (
        echo "Downloading part-$i..."
        wget -q -P ../data/data-source "${BASE_URL}/part-$i-$fileID"
        echo "Finished part-$i"
    ) &

    # Increase job count and check if we hit the limit
    ((job_count++))
    if ((job_count >= MAX_JOBS)); then
        wait
        job_count=0
    fi
done

echo "Downloading Association by DataSource Score completed."

cd ..
python3 ot-association-preprocessing.py

node gene-opentargets-disease-association-seed.js -f data/ot_overall_association_score.csv -U bolt://localhost:7687 -u neo4j -d tbep
node gene-opentargets-disease-association-seed.js -f data/ot_datasource_association_score.csv -U bolt://localhost:7687 -u neo4j -d tbep