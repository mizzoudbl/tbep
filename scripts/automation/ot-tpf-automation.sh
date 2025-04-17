#!/bin/bash
wget --recursive -np -nH -P ./data/opentargets/target-prioritization-scores/ --cut-dirs 8 ftp://ftp.ebi.ac.uk/pub/databases/opentargets/platform/latest/output/target_prioritisation
echo "Download complete. Converting Parquet files to CSV format..."
python3 ../parquet2csv.py --tps
node ../target-prioritization-column-mapper.js
echo "Conversion complete. Seeding into database..."
node ../gene-universal-seed.js -f ../data/ot_target_prioritization_score.csv -U bolt://localhost:7687 -u neo4j -d tbep --di --nh