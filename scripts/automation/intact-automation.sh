wget https://ftp.ebi.ac.uk/pub/databases/intact/current/psimitab/species/human.zip
unzip human.zip
# Remove extra file
rm human.zip human_*.txt
mv human.txt ../data/

# Run the script
python3 ../intact-automation.py
# Seeding script
node ../gene-score-seed.js -f ../data/intact_score.csv -U bolt://localhost:7687 -u neo4j -d tbep -i INT_ACT -t 'HGNC-Symbol'