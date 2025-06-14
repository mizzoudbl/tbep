> **NOTE:** It is a markdown file so it can be rendered in a markdown viewer. For VSCode, you can press `Ctrl+Shift+V` to open the markdown preview.

# Important Instructions

- Before running any script, make sure to have the necessary dependencies installed by running `npm install` or `node install`(used node here for building the scripts) in this directory.

- For using python scripts, make sure to install necessary dependencies using `pip install -r requirements.txt` ([requirements.txt](./requirements.txt)). Here, is the list of dependencies:

  - `pandas`
  - `fastparquet`

- For [gene-universal-seed](./gene-universal-seed.js) to work, you need to have the csv file inside this scripts directory as this is linked to docker volume of the neo4j database.

- Scripts can either be run using `node <script-name>` or `npm run <script-name>` which have CLI behavior and interactive prompts behavior respectively. Use `node <filename> -h` to see the help message.

- These scripts are primarily designed to be run in a local/server environment and not in a remote environment, i.e. data can't be ingested from a remote location. Though it can be deleted from a remote location.

- All these scripts are designed such that all required data for ingestion or processing is required to be placed inside [`data`](./data) directory. The scripts will look for the data in this directory and might not work if the data is not present in this directory. This is just a recommendation for those scripts which require you to specify the path of the data (though path should be given as per the scripts directory), but it is a requirement other scripts if they expect data (like python scripts, these are typically controlled by automation scripts present in [automation](./automation/) directory).

> **NOTE:** To run any of the [automation](./automation/) scripts, `wget` must be installed in the system.
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

# Updating OpenTargets Data

## Target Prioritization Scores

Run this automation script:

- [bash](./automation/ot-tpf-automation.sh)
- [powershell](./automation/ot-tpf-automation.ps1)

## Target Disease Association Scores

Run this automation script:

- [bash](./automation/ota-automation.sh)
- [powershell](./automation/ota-automation.ps1)

# Format of Files required for ingestion

## Interaction Data (Edges between genes)

- The interaction data should be in the form of a CSV file. We expect three columns in the CSV file in the following order:
  - `Gene1`: HGNC symbol or EnsemblID (can't be mix of both in the file) of the first gene in the interaction.
  - `Gene2`: HGNC symbol or EnsemblID (can't be mix of both in the file) of the second gene in the interaction.
  - `Score`: The score of the interaction.
- The CSV file should not have any header row. The first row of the CSV file should be the first interaction.
- The CSV file should not have any empty rows or columns.

**Sample Interaction file:**

```csv
ACIN1,LRRK2,0.512
ACIN1,SRPK2,0.761
```

```
ENSG00000135823,ENSG00000135824,0.5
ENSG00000135823,ENSG00000135825,0.6
```

## Universal Data (Properties of genes)

- The universal data should be in the form of a CSV file. We expect headers in the CSV file in the following order:

  - `Gene ID`: HGNC symbol or EnsemblID (can't be mix of both in the file) of the gene. You have to specify the `idType` explicitly in the ingestion script using `-t` or `--idType` (e.g. `-t HGNC-Symbol` or `-t ENSEMBL-ID`). Just here, the name of the header can be anything.
  - Now, other columns can be any property of the gene. It'll be in a matrix form. So, column name should be the of the form `<PropertyType>_<PropertyName>`. Here, `<PropertyType>` can be any of the following:
    - `TE_<PropertyName>`: Tissue Expression
    - `Pathway_<PropertyName>`: Pathway
    - `Druggability_<PropertyName>`: Druggability
    - `OT_Prioritization_<PropertyName>`: OpenTargets Target Prioritization Factors
    - `DEG_<PropertyName>`: Differential Expression Gene
    - `OpenTargets_<PropertyName>`: OpenTargets Target Disease Association

- These set of universal data present in a file can be a mix of disease dependent and disease independent data. But, it shouldn't hold data from many diseases. If it contains disease dependent data, you need to specify the disease ID using `-D` or `--disease` flag. The disease ID should be in the format of MONDO ID or any other type of ID but should not be its name. Disease Mapping of ID to its name can be uploaded separately using the `disease-mapping-seed` script.
- The CSV file should not have any empty rows or columns.
- The CSV file should have a header row.

**Sample Universal Data file:**

ID,TE_prop1,Pathway_prop2,Druggability_prop3,OT_Prioritization_prop4,DEG_prop5,OpenTargets_prop6
ENSG00000135823,0.5,0.2,0.1,0.3,0.4,0.6
ENSG00000135824,0.6,0.3,0.2,0.4,0.5,0.7
```

```csv
Gene ID,TE_prop1,Pathway_prop2,Druggability_prop3,OT_Prioritization_prop4,DEG_prop5,OpenTargets_prop6
STX6,0.5,0.2,0.1,0.3,0.4,0.6
RGS8,0.6,0.3,0.2,0.4,0.5,0.7
```

## Additional Universal Data format (for gene properties where keeping properties in matrix form is very sparse)

This is made purposefully to keep OpenTargets Target Disease Association data as keeping it in matrix form is very sparse, so here each row is a property of the gene and the value is the property value.

- The universal data should be in the form of a CSV file. We expect headers in the CSV file in the following order:
  - `Gene`: EnsemblID of the gene.
  - `Property`: The property of the gene in the format `<DiseaseID>_OpenTargets_<PropertyName>`.
  - `Value`: The value of the property.

- The CSV file should not have any header row. The first row of the CSV file should be the first interaction.
- The CSV file should not have any empty rows or columns.

**Sample OpenTargets Disease Association file:**

```csv
ENSG00000001084,DOID_0050890_OpenTargets_Overall_Association Score,0.0317992666634962
ENSG00000004142,DOID_0050890_OpenTargets_Overall_Association Score,0.0022174791281082
```

```
ENSG00000254709,EFO_0000095_OpenTargets_Gene Burden,0.7308036119330903
ENSG00000100342,DOID_10113_OpenTargets_GEL PanelApp,0.607930797611621
```

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
  node gene-reference-update.js -f data/hgnc_master_gene_list_with_uniprot.csv $DEFAULT_ARGS
  node gene-score-seed.js -f data/ppi_db_string.csv -i PPI -t ENSEMBL-ID $DEFAULT_ARGS
  node gene-score-seed.js -f data/funppi_db_string.csv -i FUN_PPI -t ENSEMBL-ID $DEFAULT_ARGS
  node gene-score-seed.js -f data/biogrid_score.csv -i BIO_GRID -t HGNC-Symbol $DEFAULT_ARGS
  node gene-score-seed.js -f data/intact_score.csv -i INT_ACT -t HGNC-Symbol $DEFAULT_ARGS
  node gene-universal-seed.js -f data/TDP_Pathway_KEGG_binary_corrected_modified_kept_rows.csv --nh --di $DEFAULT_ARGS
  node gene-universal-seed.js -f data/TDP_Pathway_reactome_binary_corrected_modified_kept_rows.csv --nh --di $DEFAULT_ARGS
  node gene-universal-seed.js -f data/TE_consensus_bulkrna_kept_rows.csv --nh --di $DEFAULT_ARGS
  node gene-universal-seed.js -f data/TE_HPA_scrna_kept_rows.csv --nh --di $DEFAULT_ARGS
  node gene-universal-seed.js -f data/Druggability.csv --nh --di $DEFAULT_ARGS
  node gene-universal-seed.js -f data/ot_25.03_target_prioritization_score.csv --nh --di $DEFAULT_ARGS
  node gene-opentargets-disease-association-seed.js -f data/ot_25.03_datasource_association_score.csv $DEFAULT_ARGS
  node gene-opentargets-disease-association-seed.js -f data/ot_25.03_overall_association_score.csv $DEFAULT_ARGS
  
  ## Some LogFC data (as per availability)
  node gene-universal-seed.js -f data/ALS_logFC_from_bill_modified_kept_genes.csv --nh $DEFAULT_ARGS -D MONDO_0004976
  node gene-universal-seed.js -f data/Mayo_diagnosis_logFC_transformed_PSP_modified_kept_genes.csv --nh $DEFAULT_ARGS -D MONDO_0019037
  node gene-universal-seed.js -f data/MSBB_diagnosis_gender_logFC_transformed_PSP_modified_kept_genes.csv --nh $DEFAULT_ARGS -D MONDO_0019037
  node gene-universal-seed.js -f data/MSBB_diagnosis_logFC_transformed_PSP_modified_kept_genes.csv --nh $DEFAULT_ARGS -D MONDO_0019037
  node gene-universal-seed.js -f data/ROSMAP_diagnosis_gender_agedeath_logFC_transformed_PSP_modified_kept_genes.csv --nh $DEFAULT_ARGS -D MONDO_0019037
  node gene-universal-seed.js -f data/ROSMAP_diagnosis_logFC_transformed_PSP_modified_kept_genes.csv --nh $DEFAULT_ARGS -D MONDO_0019037
  ########################################
  node disease-mapping-seed.js -f data/ot_25.03_disease_mapping.csv $DEFAULT_ARGS
  node property-description-update.js -f data/property_description_tbep.csv $DEFAULT_ARGS

  echo "✅ Pipeline completed successfully."
} 2>&1 | tee -a "$LOGFILE"
```


# ClickHouse Data Ingestion

```bash
# Install dependencies
pip install -r requirements.txt

# Ingest overall association scores into ClickHouse
python clickhouse-overall-association-seed.py data/ot_25.03_overall_association_score.csv data/hgnc_master_gene_list_with_uniprot.csv
```

> See the script [`clickhouse-overall-association-seed.py`](./clickhouse-overall-association-seed.py) for details and customization.