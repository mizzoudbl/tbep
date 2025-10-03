#!/bin/bash

wget https://ftp.ebi.ac.uk/pub/databases/intact/current/psimitab/species/human.zip
unzip human.zip
# Remove extra file
rm human.zip human_*.txt
mv human.txt ../data/

# Run the script
echo "Running scripts..."
cd util/
python3 intact-preprocessing.py
# Seeding script
cd ../..
python3 cli.py network seed -f data/intact_score.csv -itp INT_ACT -it HGNC-Symbol -nU bolt://localhost:7687 -nu neo4j -nd tbep