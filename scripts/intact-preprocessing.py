import re
import pandas as pd

def extract_uniprotkb_rows_with_score(input_file, output_file):
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        outfile.write("ID1,ID2,Score\n")  # Write header to output file
        for line in infile:
            columns = line.strip().split('\t')
            if columns[20] != 'psi-mi:"MI:0326"(protein)' or columns[21] != 'psi-mi:"MI:0326"(protein)':
                continue
            if columns[0].startswith('uniprotkb:') and columns[1].startswith('uniprotkb:'):
                # Extract IDs by removing the 'uniprotkb:' prefix
                id1 = columns[0].replace('uniprotkb:', '')
                id2 = columns[1].replace('uniprotkb:', '')
                if id1 == id2:
                    continue
                # Search for intact-miscore:<number> in the third column
                match = re.search(r'intact-miscore:(\d*\.?\d+)', columns[14])
                if match:
                    score = match.group(1)
                    outfile.write(f"{id1},{id2},{score}\n")

def map_uniprot_to_gene(ref_file, interaction_file, output_file):
    hgnc_df = pd.read_csv(ref_file)
    uniprot_to_symbol = dict(zip(hgnc_df['UniProt ID(supplied by UniProt)'], hgnc_df['Approved symbol']))

    interactions_df = pd.read_csv(interaction_file)

    # Step 3: Map UniProt IDs to gene symbols
    interactions_df['Symbol1'] = interactions_df['ID1'].map(uniprot_to_symbol)
    interactions_df['Symbol2'] = interactions_df['ID2'].map(uniprot_to_symbol)

    interactions_df = interactions_df.dropna(subset=['Symbol1', 'Symbol2'])
    interactions_df = interactions_df.drop_duplicates(subset=['Symbol1', 'Symbol2'])
    # Step 5: Output result
    interactions_df[['Symbol1', 'Symbol2', 'Score']].to_csv(output_file, index=False)

# Usage
extract_uniprotkb_rows_with_score('data/human.txt', 'data/human-unmapped.csv')
map_uniprot_to_gene('data/hgnc_master_gene_list_with_uniprot.csv', 'data/human-unmapped.csv', 'data/intact.csv')