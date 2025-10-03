from typing import Dict
import pandas as pd
import sys
import os
import glob
import json

def combine_parquet_files(input_path):
    """
    Combine parquet files into a single DataFrame.

    Args:
        input_path (str): Path to directory containing parquet files or a single parquet file

    Returns:
        pd.DataFrame: Combined DataFrame
    """
    try:
        parquet_files = []

        # Check if input_path is a file or directory
        if os.path.isfile(input_path) and input_path.endswith(".parquet"):
            # Single parquet file
            parquet_files = [input_path]
        elif os.path.isdir(input_path):
            # Directory of parquet files
            parquet_files = glob.glob(os.path.join(input_path, "*.parquet"))
        else:
            print(
                f"The input path {input_path} is neither a parquet file nor a directory"
            )
            sys.exit(1)

        if not parquet_files:
            print(f"No parquet files found at {input_path}")
            sys.exit(1)

        # Read and combine all parquet files
        dfs: list[pd.DataFrame] = []
        for file in parquet_files:
            print(f"Reading {file}...")
            df = pd.read_parquet(file)
            dfs.append(df)

        # Combine all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)

        # Drop rows where all columns except targetId have no values
        if "targetId" in combined_df.columns:
            # Create a subset without targetId
            subset_cols = [col for col in combined_df.columns if col != "targetId"]
            if subset_cols:  # Make sure there are other columns
                combined_df = combined_df.dropna(subset=subset_cols, how="all")
        # Write to CSV
        print(
            f"Successfully combined {len(parquet_files)} parquet files"
        )
        return combined_df

    except Exception as e:
        print(f"Error combining parquet files to CSV: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Default paths
    input_path = "../../data/opentargets/target-prioritization-scores"
    output_file = "../../data/opentargets-target-prioritization-score.csv"
    args = sys.argv[1:]

    # Override with remaining command line arguments if provided
    if len(args) > 0:
        input_path = args[0]
    if len(args) > 1:
        output_file = args[1]

    print(f"Processing from: {input_path}")
    print(f"Output will be saved to: {output_file}")

    df = combine_parquet_files(input_path)
    
    with open("../../data/mapping.json", "r") as f:
        mapping = json.load(f).get("target_prioritization_score", {})
    
    mapping: Dict[str,str] = {k: f"OT_Prioritization_{v}" for k, v in mapping.items()}
    df = df.rename(columns=mapping)

    df.to_csv(output_file, index=False)
    print(f"CSV file saved to {output_file}")