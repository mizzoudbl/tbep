wget https://ftp.ebi.ac.uk/pub/databases/intact/current/psimitab/species/human.zip
Expand-Archive -Path human.zip -DestinationPath .
# Remove extra files
Remove-Item -Path human.zip
Remove-Item -Path human_*.txt
Move-Item -Path human.txt -DestinationPath ../data/

# Run the script
python ../intact-preprocessing.py
# Seeding script
node ../gene-score-seed.js -f ../data/intact_score.csv -U 'bolt://localhost:7687' -u neo4j -d tbep -i INT_ACT -t 'HGNC-Symbol'