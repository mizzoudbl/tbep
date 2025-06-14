import pandas as pd
import requests
import sys

CLICKHOUSE_URL = 'http://localhost:8123'
TABLE_NAME = 'overall_association_score'

if len(sys.argv) != 3:
    print("Usage: python clickhouse-overall-association-seed.py <csv_file> <mapping_file>")
    sys.exit(1)

#csv file: ot_25.03_overall_association_score.csv
#mapping_file: hgnc_master_gene_list_with_uniprot.csv

csv_file = sys.argv[1]
mapping_file = sys.argv[2]

mapping_df = pd.read_csv(mapping_file, usecols=['Ensembl ID(supplied by Ensembl)', 'Approved symbol'])
mapping_df = mapping_df.rename(columns={
    'Ensembl ID(supplied by Ensembl)': 'gene_id',
    'Approved symbol': 'gene_name'
})

df = pd.read_csv(csv_file, header=None, names=['gene_id', 'raw_disease_id', 'score'])

df['disease_id'] = df['raw_disease_id'].apply(lambda x: '_'.join(str(x).split('_')[:2]))

df = df.merge(mapping_df, on='gene_id', how='left')

df = df[['gene_id', 'gene_name', 'disease_id', 'score']]
df['score'] = df['score'].astype(float)
df['gene_name'] = df['gene_name'].fillna('')


create_query = f'''
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    gene_id String,
    gene_name String,
    disease_id String,
    score Float64
) ENGINE = MergeTree()
ORDER BY (disease_id, score)
'''
resp = requests.post(f'{CLICKHOUSE_URL}', params={ 'query': create_query })
if resp.status_code != 200:
    print("Error creating table:", resp.text)
    sys.exit(1)

csv_data = df.to_csv(index=False, header=False)
insert_query = f'INSERT INTO {TABLE_NAME} FORMAT CSV'
resp = requests.post(f'{CLICKHOUSE_URL}', params={ 'query': insert_query }, data=csv_data.encode('utf-8'))

if resp.status_code == 200:
    print(f'Inserted {len(df)} rows from {csv_file}.')
else:
    print("Error inserting data:", resp.text)