wget --recursive -np -nH -P ./data/opentargets/target-prioritization-scores/ --cut-dirs 8 ftp://ftp.ebi.ac.uk/pub/databases/opentargets/platform/latest/output/target_prioritisation
Write-Host "Download complete. Converting Parquet files to CSV format..."
python ../parquet2csv.py --tps
node ../target-prioritization-column-mapper.js
Write-Host "Conversion complete. Seeding into database..."
node ../gene-universal-seed.js -f ../data/opentargets_target_prioritization_score.csv -U bolt://localhost:7687 -u neo4j -d tbep --di --nh