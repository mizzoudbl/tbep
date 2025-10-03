wget https://downloads.thebiogrid.org/Download/BioGRID/Latest-Release/BIOGRID-ORGANISM-LATEST.tab3.zip
# Unzip the downloaded file
Expand-Archive -Path BIOGRID-ORGANISM-LATEST.tab3.zip -DestinationPath .
# Remove extra files
Remove-Item -Path BIOGRID-ORGANISM-LATEST.tab3.zip
Move-Item -Path BIOGRID-ORGANISM-Homo_sapiens-*.tab3.txt ../data/BIOGRID-ORGANISM-Homo_sapiens-LATEST.tab3.tsv

# Run the script
Set-Location util
python biogrid-preprocessing.py
# Seeding script
Set-Location ../..
python cli.py network seed -f data/biogrid_score.csv -itp BIO_GRID -it HGNC-Symbol -nU bolt://localhost:7687 -nu neo4j -nd tbep
