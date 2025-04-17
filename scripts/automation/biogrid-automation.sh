#!/bin/bash
wget https://downloads.thebiogrid.org/Download/BioGRID/Latest-Release/BIOGRID-ORGANISM-LATEST.tab3.zip

echo "Download complete, unzipping..."

unzip BIOGRID-ORGANISM-LATEST.tab3.zip
mv BIOGRID-ORGANISM-Homo_sapiens-*.tab3.txt ../data/BIOGRID-ORGANISM-Homo_sapiens-LATEST.tab3.tsv

# Remove extra files
rm BIOGRID-ORGANISM-*.{txt,zip}

# Run the script
echo "Running script..."
python3 ../biogrid-preprocessing.py
# Seeding script
node ../gene-score-seed.js -f ../data/biogrid_score.csv -U bolt://localhost:7687 -u neo4j -d tbep -i BIOGRID -t 'HGNC-Symbol'