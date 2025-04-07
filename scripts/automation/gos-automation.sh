# Get the password from input
read -s "Enter the password: " pw
echo

# Get all CSV files in the data directory
for file in ../data/data/opentargets/target-association-scores/*.csv; do
    # Check if the file is not in the exclude list
    if [ -e "$file" ]; then
        echo "Processing file: $(basename "$file")"
        pnpm gos -f "$file" -u neo4j -p "$pw" -d "tbep" -U "bolt://localhost:7687" --nh
    fi
done
