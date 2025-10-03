> **NOTE:** It is a markdown file so it can be rendered in a markdown viewer. For VSCode, you can press `Ctrl+Shift+V` to open the markdown preview.

# Important Instructions

- Install Python dependencies with uv command `uv sync`
  before running the CLI. Required packages include:

  - `pandas`
  - `clickhouse-connect`
  - `neo4j`
  - `click`
  - `inquirer`
  - `rich`

  If you don't have `uv` command, install by just using pip using following command:

  ```bash
  pip install pandas clickhouse-connect neo4j click inquirer rich
  ```

- Run workflow commands via the Python CLI: `python cli.py <group> <command>` (for example `python cli.py universal seed --help`). Use `python cli.py --help` to list top-level groups and options.

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
    - `<DiseaseId>_DEG_<PropertyName>`: Differential Expression Gene
    - `<DiseaseId>_OpenTargets_<PropertyName>`: OpenTargets Target Disease Association

- These set of universal data present in a file can be a mix of disease dependent and disease independent data. But, it shouldn't hold data from many diseases. If it contains disease dependent data, you need to specify the disease ID using `-D` or `--disease` flag. The disease ID should be in the format of MONDO ID or any other type of ID but should not be its name. Disease Mapping of ID to its name can be uploaded separately using the `disease-mapping-seed` script.
- The CSV file should not have any empty rows or columns.
- The CSV file should have a header row.

**Sample Universal Data file:**

```csv
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
gene_id,property_name,value
ENSG00000001084,DOID_0050890_OpenTargets_Overall_Association Score,0.0317992666634962
ENSG00000004142,DOID_0050890_OpenTargets_Overall_Association Score,0.0022174791281082
```

```
gene_id,property_name,value
ENSG00000254709,EFO_0000095_OpenTargets_Gene Burden,0.7308036119330903
ENSG00000100342,DOID_10113_OpenTargets_GEL PanelApp,0.607930797611621
```

# Database Ingestion Order

Here, is a script which describes the order in which database should be prepared and ingested. This is important as some scripts depend on the data from other scripts.

```bash
WORKDIR="/path/to/this/directory"  # <-- Change this
CLICKHOUSE_PASSWORD="your_password"  # <-- Change this
NEO4J_PASSWORD="your_password"  # <-- Change this
LOGFILE="$WORKDIR/data_pipeline_$(date +%F_%T).log"

CLICKHOUSE_ARGS="--ch localhost --cp 8123 --cd default --cu default --cP $CLICKHOUSE_PASSWORD"
NEO4J_ARGS="-nU bolt://localhost:7687 -nu neo4j -nP $NEO4J_PASSWORD -nd tbep"

cd "$WORKDIR"
echo "Running pipeline from: $WORKDIR" | tee -a "$LOGFILE"

{
  python cli.py network update-reference-genome -f data/hgnc_master_gene_list_with_uniprot.csv $NEO4J_ARGS
  python cli.py network seed -f data/ppi_db_string.csv -itp FUN_PPI -it ENSEMBL-ID $NEO4J_ARGS
  python cli.py network seed -f data/funppi_db_string.csv -itp PPI -it ENSEMBL-ID $NEO4J_ARGS
  python cli.py network seed -f data/biogrid_score.csv -itp BIO_GRID -it HGNC-Symbol $NEO4J_ARGS
  python cli.py network seed -f data/intact_score.csv -itp INT_ACT -it HGNC-Symbol $NEO4J_ARGS
  python cli.py universal seed -f data/TDP_Pathway_KEGG_binary_corrected_modified_kept_rows.csv -fmt dense $CLICKHOUSE_ARGS $NEO4J_ARGS
  python cli.py universal seed -f data/TDP_Pathway_reactome_binary_corrected_modified_kept_rows.csv $CLICKHOUSE_ARGS $NEO4J_ARGS
  python cli.py universal seed -f data/TE_consensus_bulkrna_kept_rows.csv $CLICKHOUSE_ARGS $NEO4J_ARGS
  python cli.py universal seed -f data/TE_HPA_scrna_kept_rows.csv $CLICKHOUSE_ARGS $NEO4J_ARGS
  python cli.py universal seed -f data/Druggability.csv $CLICKHOUSE_ARGS $NEO4J_ARGS
  python cli.py universal seed -f data/ot_25.03_target_prioritization_score.csv $CLICKHOUSE_ARGS $NEO4J_ARGS
  python cli.py opentargets seed -f data/ot_25.03_datasource_association_score.csv -fmt sparse -t datasource_association_score $CLICKHOUSE_ARGS $NEO4J_ARGS
  python cli.py opentargets seed -f data/ot_25.03_overall_association_score.csv -fmt sparse -t overall_association_score $CLICKHOUSE_ARGS $NEO4J_ARGS

  sed -i '1s/logFC_\./MONDO_0004976_DEG_\./g' data/ALS_logFC_from_bill_modified_kept_genes.csv
  python cli.py universal seed -f data/ALS_logFC_from_bill_modified_kept_genes.csv $CLICKHOUSE_ARGS $NEO4J_ARGS
  sed -i '1s/logFC_\./MONDO_0019037_DEG_\./g' data/Mayo_diagnosis_logFC_transformed_PSP_modified_kept_genes.csv
  python cli.py universal seed -f data/Mayo_diagnosis_logFC_transformed_PSP_modified_kept_genes.csv -d MONDO_0019037 $CLICKHOUSE_ARGS $NEO4J_ARGS
  sed -i '1s/logFC_\./MONDO_0019037_DEG_\./g' data/MSBB_diagnosis_gender_logFC_transformed_PSP_modified_kept_genes.csv
  python cli.py universal seed -f data/MSBB_diagnosis_gender_logFC_transformed_PSP_modified_kept_genes.csv -d MONDO_0019037 $CLICKHOUSE_ARGS $NEO4J_ARGS
  sed -i '1s/logFC_\./MONDO_0019037_DEG_\./g' data/MSBB_diagnosis_gender_logFC_transformed_PSP_modified_kept_genes.csv
  python cli.py universal seed -f data/MSBB_diagnosis_gender_logFC_transformed_PSP_modified_kept_genes.csv -d MONDO_0019037 $CLICKHOUSE_ARGS $NEO4J_ARGS
  sed -i '1s/logFC_\./MONDO_0019037_DEG_\./g' data/MSBB_diagnosis_logFC_transformed_PSP_modified_kept_genes.csv
  python cli.py universal seed -f data/MSBB_diagnosis_logFC_transformed_PSP_modified_kept_genes.csv -d MONDO_0019037 $CLICKHOUSE_ARGS $NEO4J_ARGS
  sed -i '1s/logFC_\./MONDO_0019037_DEG_\./g' data/ROSMAP_diagnosis_gender_agedeath_logFC_transformed_PSP_modified_kept_genes.csv
  python cli.py universal seed -f data/ROSMAP_diagnosis_gender_agedeath_logFC_transformed_PSP_modified_kept_genes.csv -d MONDO_0019037 $CLICKHOUSE_ARGS $NEO4J_ARGS
  sed -i '1s/logFC_\./MONDO_0019037_DEG_\./g' data/ROSMAP_diagnosis_logFC_transformed_PSP_modified_kept_genes.csv
  python cli.py universal seed -f data/ROSMAP_diagnosis_logFC_transformed_PSP_modified_kept_genes.csv -d MONDO_0019037 $CLICKHOUSE_ARGS $NEO4J_ARGS

  python cli.py network update-disease-metadata -f data/ot_25.03_disease_mapping.csv $NEO4J_ARGS
  python cli.py network update-property-metadata -f data/property_description_tbep.csv $NEO4J_ARGS
} 2>&1 | tee -a "$LOGFILE"
```
