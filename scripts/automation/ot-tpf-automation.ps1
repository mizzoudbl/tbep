wget --recursive -np -nH -P ./data/opentargets/target-prioritization-scores/ --cut-dirs 8 ftp://ftp.ebi.ac.uk/pub/databases/opentargets/platform/latest/output/target_prioritisation
Write-Host "Download complete. Converting Parquet files to CSV format..."
Set-Location util
python ot-prioritization-preprocessing.py
Set-Location ../..
Write-Host "Conversion complete. Seeding into database..."
python3 cli.py universal seed --file data/opentargets-target-prioritization-score.csv --format dense