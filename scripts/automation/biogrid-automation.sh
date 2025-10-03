#!/bin/bash
wget https://downloads.thebiogrid.org/Download/BioGRID/Latest-Release/BIOGRID-ORGANISM-LATEST.tab3.zip

echo "Download complete, unzipping..."

unzip BIOGRID-ORGANISM-LATEST.tab3.zip
mv BIOGRID-ORGANISM-Homo_sapiens-*.tab3.txt ../data/BIOGRID-ORGANISM-Homo_sapiens-LATEST.tab3.tsv

# Remove extra files
rm BIOGRID-ORGANISM-*.{txt,zip}

# Run the script
echo "Running script..."
cd util/
python3 biogrid-preprocessing.py
# Seeding script
cd ../..
python3 cli.py network seed -f data/biogrid_score.csv -itp BIO_GRID -it HGNC-Symbol -nU bolt://localhost:7687 -nu neo4j -nd tbep
