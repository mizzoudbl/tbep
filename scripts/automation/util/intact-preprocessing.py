import re
import pandas as pd


def extract_uniprotkb_rows_with_score(input_file, output_file):
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        outfile.write("ID1,ID2,Score\n")  # Write header to output file
        for line in infile:
            columns = line.strip().split("\t")
            if (
                columns[20] != 'psi-mi:"MI:0326"(protein)'
                or columns[21] != 'psi-mi:"MI:0326"(protein)'
            ):
                continue
            if columns[0].startswith("uniprotkb:") and columns[1].startswith(
                "uniprotkb:"
            ):
                # Extract IDs by removing the 'uniprotkb:' prefix
                id1 = columns[0].replace("uniprotkb:", "")
                id2 = columns[1].replace("uniprotkb:", "")
                if id1 == id2:
                    continue
                # Search for intact-miscore:<number> in the third column
                match = re.search(r"intact-miscore:(\d*\.?\d+)", columns[14])
                if match:
                    score = match.group(1)
                    outfile.write(f"{id1},{id2},{score}\n")


def map_uniprot_to_gene(ref_file, interaction_file, output_file):
    hgnc_df = pd.read_csv(ref_file)[
        ["UniProt ID(supplied by UniProt)", "Approved symbol"]
    ]
    hgnc_df = hgnc_df.dropna()
    uniprot_to_symbol = dict(
        zip(hgnc_df["UniProt ID(supplied by UniProt)"], hgnc_df["Approved symbol"])
    )
    print(f"Mapping {len(uniprot_to_symbol)} UniProt IDs to gene symbols")
    df = pd.read_csv(interaction_file)
    print(f"Original file has {len(df)} rows")
    # Step 3: Map UniProt IDs to gene symbols
    df.loc[:, "ID1"] = df["ID1"].map(uniprot_to_symbol)
    df.loc[:, "ID2"] = df["ID2"].map(uniprot_to_symbol)
    df = df.dropna()
    print(f"After mapping, {len(df)} rows remain")
    print("Checking for unordered duplicates (gene1,gene2 vs gene2,gene1)...")
    # Extract protein pairs and create a new column with sorted pairs
    df = df[(df["Score"] >= 0.15) & (df["Score"] <= 1.0)]
    print(
        f"After filtering for scores between 0.15 and 1.0 (inclusive), {len(df)} rows remain"
    )
    df["sorted_pair"] = df.apply(
        lambda row: tuple(sorted([row.iloc[0], row.iloc[1]])), axis=1
    )
    # Count occurrences of each sorted pair
    pair_counts = df["sorted_pair"].value_counts()
    # Find duplicated pairs (count > 1)
    duplicated_pairs = pair_counts[pair_counts > 1].index.tolist()
    print(f"Found {len(duplicated_pairs)} unique pairs that appear in different orders")
    print(
        f"Total duplicated rows: {sum(pair_counts[pair_counts > 1].values) - len(duplicated_pairs)}"
    )

    df = df.loc[df.groupby("sorted_pair")["Score"].idxmax()]
    print(f"After keeping only the maximum score for each pair, {len(df)} rows remain")
    # Export the final dataframe without the sorted_pair column and without headers
    df = df.drop(columns=["sorted_pair"])
    # Step 5: Output result
    df.to_csv(output_file, index=False, header=False)


# Usage
extract_uniprotkb_rows_with_score("../../data/human.txt", "../../data/human-unmapped.csv")
map_uniprot_to_gene(
    "../../data/hgnc_master_gene_list_with_uniprot.csv",
    "../../data/human-unmapped.csv",
    "../../data/intact_score.csv",
)
