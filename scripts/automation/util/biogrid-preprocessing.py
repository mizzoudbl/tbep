import pandas as pd


def extract_rows_with_score(input_file, output_file):
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        for line in infile:
            columns = line.strip().split("\t")
            score = columns[18]
            if score == "-":
                continue
            id1 = columns[7]
            id2 = columns[8]
            outfile.write(f"{id1},{id2},{score}\n")


def filter_map_with_reference(ref_file, input_file, output_file):
    hgnc_df = pd.read_csv(ref_file)[["Previous symbols", "Approved symbol"]]

    PREV_TO_NEW_SYMBOL = {}
    ID1 = "Official Symbol Interactor A"
    ID2 = "Official Symbol Interactor B"
    score = "Score"
    for _, row in hgnc_df.iterrows():
        approved_symbol = row["Approved symbol"]
        PREV_TO_NEW_SYMBOL[approved_symbol] = approved_symbol

        if pd.isna(row["Previous symbols"]):
            continue
        prev_symbols = row["Previous symbols"].split(",")
        prev_symbols = [symbol.strip() for symbol in prev_symbols]
        for prev_symbol in prev_symbols:
            PREV_TO_NEW_SYMBOL[prev_symbol] = approved_symbol

    print(f"Mapping {len(PREV_TO_NEW_SYMBOL)} symbols")
    df = pd.read_csv(input_file)
    df[score] = pd.to_numeric(df[score]).round(3)
    print(f"Original file has {len(df)} rows")
    df.loc[:, ID1] = df[ID1].map(PREV_TO_NEW_SYMBOL)
    df.loc[:, ID2] = df[ID2].map(PREV_TO_NEW_SYMBOL)
    df = df.dropna()

    print(f"After mapping, {len(df)} rows remain")
    print("Checking for unordered duplicates (gene1,gene2 vs gene2,gene1)...")
    # Extract protein pairs and create a new column with sorted pairs
    df = df[(df[score] >= 0.15) & (df[score] <= 1.0)]
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

    df = df.loc[df.groupby("sorted_pair")[score].idxmax()]
    print(f"After keeping only the maximum score for each pair, {len(df)} rows remain")
    # Export the final dataframe without the sorted_pair column and without headers
    df = df.drop(columns=["sorted_pair"])
    df.to_csv(output_file, index=False, header=False)


# Usage
extract_rows_with_score(
    "../../data/BIOGRID-ORGANISM-Homo_sapiens-LATEST.tab3.tsv",
    "../../data/BIOGRID-ORGANISM-Homo_sapiens-LATEST.tab3.csv",
)
filter_map_with_reference(
    "../../data/hgnc_master_gene_list_with_uniprot.csv",
    "../../data/BIOGRID-ORGANISM-Homo_sapiens-LATEST.tab3.csv",
    "../../data/biogrid_score.csv",
)
