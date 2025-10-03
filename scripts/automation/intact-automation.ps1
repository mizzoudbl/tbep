wget https://ftp.ebi.ac.uk/pub/databases/intact/current/psimitab/species/human.zip
Expand-Archive -Path human.zip -DestinationPath .
# Remove extra files
Remove-Item -Path human.zip
Remove-Item -Path human_*.txt
Move-Item -Path human.txt -DestinationPath ../data/

# Run the script
Set-Location util
python intact-preprocessing.py
# Seeding script
Set-Location ../..
python cli.py network seed -f data/intact_score.csv -itp INT_ACT -it HGNC-Symbol  -nU bolt://localhost:7687 -nu neo4j -nd tbep
