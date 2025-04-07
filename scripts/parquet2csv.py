import pandas as pd
import sys
import os
import glob

def combine_parquet_files(input_path, output_file):
    """
    Combine parquet files into a single CSV file.
    
    Args:
        input_path (str): Path to directory containing parquet files or a single parquet file
        output_file (str): Path for the output combined CSV file
    
    Returns:
        str: Path to the output CSV file
    """
    try:
        parquet_files = []
        
        # Check if input_path is a file or directory
        if os.path.isfile(input_path) and input_path.endswith('.parquet'):
            # Single parquet file
            parquet_files = [input_path]
        elif os.path.isdir(input_path):
            # Directory of parquet files
            parquet_files = glob.glob(os.path.join(input_path, "*.parquet"))
        else:
            print(f"The input path {input_path} is neither a parquet file nor a directory")
            return None
        
        if not parquet_files:
            print(f"No parquet files found at {input_path}")
            return None
        
        # Read and combine all parquet files
        dfs = []
        for file in parquet_files:
            print(f"Reading {file}...")
            df = pd.read_parquet(file)
            dfs.append(df)
        
        # Combine all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Drop rows where all columns except targetId have no values
        if 'targetId' in combined_df.columns:
            # Create a subset without targetId
            subset_cols = [col for col in combined_df.columns if col != 'targetId']
            if subset_cols:  # Make sure there are other columns
                combined_df = combined_df.dropna(subset=subset_cols, how='all')
        # Write to CSV
        combined_df.to_csv(output_file, index=False)
        print(f"Successfully combined {len(parquet_files)} parquet files into {output_file}")
        return output_file
    
    except Exception as e:
        print(f"Error combining parquet files to CSV: {str(e)}")
        return None

if __name__ == "__main__":
    # Default paths
    input_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data/opentargets/target-prioritization-scores"))
    output_file = os.path.join(os.path.dirname(__file__), "data/opentargets-target-prioritization-score.csv")
    
    # Override with command line arguments if provided
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    print(f"Processing from: {input_path}")
    print(f"Output will be saved to: {output_file}")
    
    combine_parquet_files(input_path, output_file)