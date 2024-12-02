#!/bin/bash

for file in *.csv; do
    if [ -f "$file" ]; then
        echo "Processing file: $file"
        pnpm gus -f "$file" -u neo4j -p <password> -d tbep -U bolt://localhost:7687
    fi
done
