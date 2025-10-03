from typing import Dict
import pandas as pd
import os


def combine_parquet_files(input_path, output_file):
    """
    Combine parquet files into a single CSV file.

    Args:
        input_path (str): Path to directory containing parquet files or a single parquet file
        output_file (str): Path for the output combined CSV file

    Returns:
        str: Path to the output CSV file
    """

    # Check if input_path is a directory or a single file
    if os.path.isdir(input_path):
        # Combine all parquet files in the directory
        df = pd.concat(
            [
                pd.read_parquet(os.path.join(input_path, f))
                for f in os.listdir(input_path)
                if f.endswith(".parquet")
            ]
        )
    else:
        # Read the single parquet file
        df = pd.read_parquet(input_path)

    # Save the combined dataframe to CSV
    df.to_csv(output_file, index=False)

    return output_file


def process_csv_rows(csv_file, data_source=False):
    """
    Process each row of the CSV file and print the values.

    Args:
        csv_file (str): Path to the CSV file
        data_source (bool): Flag to indicate if the file is data source specific
    """
    # Read the CSV file
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_file}' not found. Please ensure the file exists.")
        return

    if data_source:
        import json

        # Load the mapping dictionary from JSON file
        try:
            with open("../../data/mapping.json", "r") as f:
                mapping: Dict[str, str] = json.load(f).get(
                    "target_disease_association", {}
                )
        except FileNotFoundError:
            print(
                "Error: mapping.json file not found. Please ensure the file exists in the data/ directory."
            )
            return
        except json.JSONDecodeError:
            print("Error: mapping.json contains invalid JSON format.")
            return

        # Process data source specific information
        # Assuming we need to extract the datasource from each row and map it
        # Add the data source name to the disease ID
        df["property_name"] = df["datasourceId"].map(mapping)
        df = df.dropna(subset=["property_name"])
        df = df.rename(columns={"targetId": "gene_id", "diseaseId": "disease_id"})
        df[["gene_id", "property_name", "disease_id", "score"]].to_csv(
            "../../data/ot_datasource_association_score.csv", index=False, header=True
        )
    else:
        df[["gene_id", "disease_id", "score"]].to_csv(
            "../../data/ot_overall_association_score.csv", index=False, header=True
        )


# Example usage
data_source_parquet_dir = "../../data/data-source"
merged_datasource_csv = "data-source.csv"
combine_parquet_files(data_source_parquet_dir, merged_datasource_csv)

overall_parquet_dir = "../../data/overall"
merged_overall_association_scores_csv = "overall.csv"
combine_parquet_files(overall_parquet_dir, merged_overall_association_scores_csv)

process_csv_rows(merged_datasource_csv, data_source=True)
process_csv_rows(merged_overall_association_scores_csv, data_source=False)
