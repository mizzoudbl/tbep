wget https://downloads.thebiogrid.org/Download/BioGRID/Latest-Release/BIOGRID-ORGANISM-LATEST.tab3.zip
# Unzip the downloaded file
Expand-Archive -Path BIOGRID-ORGANISM-LATEST.tab3.zip -DestinationPath .
# Remove extra files
Remove-Item -Path BIOGRID-ORGANISM-LATEST.tab3.zip
Move-Item -Path BIOGRID-ORGANISM-Homo_sapiens-*.tab3.txt ../data/BIOGRID-ORGANISM-Homo_sapiens-LATEST.tab3.tsv

# Run the script
python ../biogrid-preprocessing.py
# Seeding script
node ../gene-score-seed.js -f ../data/biogrid_score.csv -U 'bolt://localhost:7687' -u neo4j -d tbep -i BIO_GRID -t 'HGNC-Symbol'
