> **NOTE:** It is a markdown file so it can be rendered in a markdown viewer. For VSCode, you can press `Ctrl+Shift+V` to open the markdown preview.

# Important Instructions

- Before running any script, make sure to have the necessary dependencies installed by running `npm install` or `pnpm install`(used pnpm here for building the scripts) in this directory.

- For using python scripts, make sure to install necessary dependencies using `pip install -r requirements.txt` ([requirements.txt](./requirements.txt)). Here, is the list of dependencies:

  - `pandas`
  - `fastparquet`

- For [gene-universal-seed](./gene-universal-seed.js) to work, you need to have the csv file inside this scripts directory as this is linked to docker volume of the neo4j database.

- Scripts can either be run using `node <script-name>` or `npm run <script-name>` which have CLI behavior and interactive prompts behavior respectively. Use `node <filename> -h` to see the help message.

- These scripts are primarily designed to be run in a local/server environment and not in a remote environment, i.e. data can't be ingested from a remote location. Though it can be deleted from a remote location.

- All these scripts are designed such that all required data for ingestion or processing is required to be placed inside [`data`](./data) directory. The scripts will look for the data in this directory and might not work if the data is not present in this directory. This is just a recommendation for those scripts which require you to specify the path of the data (though path should be given as per the scripts directory), but it is a requirement other scripts if they expect data (like python scripts, these are typically controlled by automation scripts present in [automation](./automation/) directory).

# Updating OpenTargets Data

## Target Prioritization Scores

Run this automation script:

- [bash](./automation/tps-automation.sh)
- [powershell](./automation/tps-automation.ps1)

> **NOTE:** Any of the script can be run, but both requires `wget` to be installed in the system.
> To install `wget`:
>
> ```bash
> # Linux
> sudo apt-get install wget
> ```
>
> ```powershell
> # Windows
> winget install --id GNU.Wget2
> Set-Alias -Name wget -Value wget2
> ```

# FAQ & Acronyms

- _gus:_ Gene Universal Seeding
- _gss:_ Gene Score Seeding
- _gud:_ Gene Universal Deletion
- _rgu:_ Reference Genome Update
- _dms:_ Disease Mapping Seeding
- _gottdas:_ Gene OpenTargets Target Disease Association Seeding
- _ot-tpf:_ OpenTargets Target Prioritization Factors
- _ot-tda:_ OpenTargets Target Disease Association
- _rgv:_ Reference Genome Verification
- _pdu:_ Property Description Update

# Database Ingestion Order

Here, is a script which describes the order in which database should be prepared and ingested. This is important as some scripts depend on the data from other scripts. The order is as follows:

1. `rgu` - Reference Genome Update
2. `gss` - Gene Score Seeding
3. `gus` - Gene Universal Seeding
4. `gottdas` - Gene OpenTargets Target Disease Association Seeding
5. `dms` - Disease Mapping Seeding
6. `pdu` - Property Description Update

```bash
# Absolute path to the working directory (adjust as needed)
WORKDIR="/path/to/this/directory"  # <-- Change this
# Neo4j password (change this to your actual password)
PASSWORD="your_password"  # <-- Change this
# Log file
LOGFILE="$WORKDIR/data_pipeline_$(date +%F_%T).log"

# Commands
DEFAULT_ARGS="-U bolt://localhost:7687 -u neo4j -p $PASSWORD -d tbep"

cd "$WORKDIR"
echo "Running pipeline from: $WORKDIR" | tee -a "$LOGFILE"

{
  pnpm rgu -f data/hgnc_master_gene_list_with_uniprot.csv $DEFAULT_ARGS
  pnpm gss -f data/ppi_db_string.csv -i PPI -t ENSEMBL-ID $DEFAULT_ARGS
  pnpm gss -f data/funppi_db_string.csv -i FUN_PPI -t ENSEMBL-ID $DEFAULT_ARGS
  pnpm gss -f data/biogrid_score.csv -i BIO_GRID -t HGNC-Symbol $DEFAULT_ARGS
  pnpm gss -f data/intact_score.csv -i INT_ACT -t HGNC-Symbol $DEFAULT_ARGS
  pnpm gus -f data/TDP_Pathway_KEGG_binary_corrected_modified_kept_rows.csv --nh --di $DEFAULT_ARGS
  pnpm gus -f data/TDP_Pathway_reactome_binary_corrected_modified_kept_rows.csv --nh --di $DEFAULT_ARGS
  pnpm gus -f data/TE_consensus_bulkrna_kept_rows.csv --nh --di $DEFAULT_ARGS
  pnpm gus -f data/TE_HPA_scrna_kept_rows.csv --nh --di $DEFAULT_ARGS
  pnpm gus -f data/Druggability.csv --nh --di $DEFAULT_ARGS
  pnpm gus -f data/ot_25.03_target_prioritization_score.csv --nh --di $DEFAULT_ARGS
  pnpm gottdas -f data/ot_25.03_datasource_association_score.csv $DEFAULT_ARGS
  pnpm gottdas -f data/ot_25.03_overall_association_score.csv $DEFAULT_ARGS
  
  ## Some LogFC data (as per availability)
  pnpm gus -f data/ALS_logFC_from_bill_modified_kept_genes.csv --nh $DEFAULT_ARGS -D MONDO_0004976
  pnpm gus -f data/Mayo_diagnosis_logFC_transformed_PSP_modified_kept_genes.csv --nh $DEFAULT_ARGS -D MONDO_0019037
  pnpm gus -f data/MSBB_diagnosis_gender_logFC_transformed_PSP_modified_kept_genes.csv --nh $DEFAULT_ARGS -D MONDO_0019037
  pnpm gus -f data/MSBB_diagnosis_logFC_transformed_PSP_modified_kept_genes.csv --nh $DEFAULT_ARGS -D MONDO_0019037
  pnpm gus -f data/ROSMAP_diagnosis_gender_agedeath_logFC_transformed_PSP_modified_kept_genes.csv --nh $DEFAULT_ARGS -D MONDO_0019037
  pnpm gus -f data/ROSMAP_diagnosis_logFC_transformed_PSP_modified_kept_genes.csv --nh $DEFAULT_ARGS -D MONDO_0019037
  ########################################
  pnpm dms -f data/ot_25.03_disease_mapping.csv $DEFAULT_ARGS
  pnpm pdu -f data/property_description_tbep.csv $DEFAULT_ARGS

  echo "✅ Pipeline completed successfully."
} 2>&1 | tee -a "$LOGFILE"
```
