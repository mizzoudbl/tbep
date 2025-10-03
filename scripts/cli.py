#!/usr/bin/env python3
"""
ClickHouse Gene Data Seeder CLI

A comprehensive CLI tool for ingesting gene data into ClickHouse tables
with support for both dense and sparse formats.
"""

from collections import defaultdict
import click
import pandas as pd
import clickhouse_connect
import inquirer
import sys
from typing import Dict, List, LiteralString, Optional, Union, Any
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from neo4j import GraphDatabase

console = Console()

# Table mappings based on prefixes
TABLE_MAPPINGS = {
    "Pathway": "pathway",
    "Druggability": "druggability",
    "Druggability_Score": "druggability",
    "TE": "tissue_specificity",
    "OT_Prioritization": "target_prioritization_factors",
}

TABLE_CATEGORY_MAPPING = {
    "pathway": "Pathway",
    "druggability": "Druggability",
    "tissue_specificity": "TE",
    "target_prioritization_factors": "OT_Prioritization",
    "differential_expression": "DEG",
    "overall_association_score": "OpenTargets",
    "datasource_association_score": "OpenTargets",
}

# Disease-dependent fields (require disease context)
DISEASE_DEPENDENT_FIELDS = ["DEG", "OpenTargets"]

# Disease-independent fields
DISEASE_INDEPENDENT_FIELDS = [
    "Pathway",
    "Druggability",
    "Druggability_Score",
    "TE",
    "OT_Prioritization",
]


class Neo4jSeeder:
    def __init__(self, uri: str, username: str, password: str, database: str = "tbep"):
        """Initialize Neo4j connection"""
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.database = database

    def close(self):
        """Close Neo4j connection"""
        self.driver.close()

    def test_connection(self) -> bool:
        """Test Neo4j connection"""
        try:
            self.driver.execute_query("RETURN 1")
            return True
        except Exception as e:
            console.print(f"[red]Connection failed: {e}[/red]")
            return False

    def seed_properties(
        self,
        common_properties: List[Dict[str, str]],
        disease_properties: Dict[str, List[Dict[str, str]]],
    ) -> Dict[str, Any]:
        """Create Property nodes and Disease relationships based on column mappings"""

        # Create Property nodes and relationships in Neo4j
        with self.driver.session(database=self.database) as session:
            # Create disease-specific properties and relationships
            for disease_id, properties in disease_properties.items():
                console.print(
                    f"[blue]Creating {len(properties)} disease-specific properties for {disease_id}...[/blue]"
                )
                session.run(
                    """
                    MERGE (d:Disease { ID: $disease_id })
                    WITH d
                    UNWIND $properties AS prop
                    MERGE (p:Property { name: prop.name, category: prop.category })
                    MERGE (d)-[:HAS_PROPERTY]->(p)
                    """,
                    disease_id=disease_id,
                    properties=properties,
                )

            # Create common properties
            if common_properties:
                console.print(
                    f"[blue]Creating {len(common_properties)} common properties...[/blue]"
                )
                session.run(
                    """
                    UNWIND $properties AS prop
                    MERGE (p:Common:Property { name: prop.name, category: prop.category })
                    """,
                    properties=common_properties,
                )

        return {
            "common": [p["name"] for p in common_properties],
            "disease_specific": {
                k: [p["name"] for p in v] for k, v in disease_properties.items()
            },
        }


class ClickHouseSeeder:
    def __init__(
        self, host: str, port: int, database: str, username: str, password: str
    ):
        """Initialize ClickHouse connection"""
        self.client = clickhouse_connect.get_client(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
        )
        self.database = database

    def close(self):
        """Close ClickHouse connection"""
        self.client.close_connections()

    def test_connection(self) -> bool:
        """Test ClickHouse connection"""
        return self.client.ping()


def detect_format(df: pd.DataFrame, id_column: str) -> str:
    """Auto-detect if data is in dense or sparse format"""
    columns = [col for col in df.columns if col != id_column]

    # Check if we have property_name column (sparse format indicator)
    if "property_name" in df.columns or "datasource_id" in df.columns:
        return "sparse"

    # Check for prefixes in column names (dense format indicator)
    has_prefixes = any(
        any(
            col.lower().startswith(f"{prefix.lower()}_")
            for prefix in TABLE_MAPPINGS.keys()
        )
        for col in columns
    )
    # Check for disease-dependent patterns that might not follow prefix format
    for col in columns:
        if len(col.split("_DEG_")) >= 2 or len(col.split("_OpenTargets_")) >= 2:
            has_prefixes = True
            break

    if has_prefixes:
        return "dense"

    return "unknown"


def parse_column_mapping(
    columns: List[str],
) -> Dict[str, Dict[str, Union[str, bool]]]:
    """Parse column names and map them to appropriate tables"""
    column_mapping = {}

    for col in columns:
        table_name = None
        property_name = None
        disease_id = None

        # Check for disease-specific patterns: <disease>_OpenTargets_<property> or <disease>_DEG_<property>
        if "_OpenTargets_" in col:
            parts = col.split("_OpenTargets_")
            if len(parts) == 2:
                disease_id = parts[0]
                target_part = parts[1]

                # Check if it's Overall Association Score
                if target_part.lower() in [
                    "overall_association_score",
                    "overall association score",
                ]:
                    table_name = "overall_association_score"
                    property_name = "overall"  # Standardize property name
                else:
                    # It's a datasource-specific score
                    table_name = "datasource_association_score"
                    property_name = target_part  # This becomes the datasource_id
        elif "_DEG_" in col:
            parts = col.split("_DEG_")
            if len(parts) == 2:
                disease_id = parts[0]
                property_name = parts[1]
                table_name = "differential_expression"

        # Handle disease-independent columns
        if not table_name:
            for prefix, table in TABLE_MAPPINGS.items():
                if col.lower().startswith(f"{prefix.lower()}_"):
                    property_name = col[len(prefix) + 1 :]
                    table_name = table
                    break

        if table_name:
            mapping_info = {
                "table": table_name,
                "property_name": property_name,
                "disease_id": disease_id,
                "requires_disease": table_name
                in [
                    "differential_expression",
                    "overall_association_score",
                    "datasource_association_score",
                ],
                "requires_mapping": table_name
                in ["overall_association_score", "datasource_association_score"],
            }

            # Add datasource_id for datasource_association_score table
            if table_name == "datasource_association_score":
                mapping_info["datasource_id"] = property_name

            column_mapping[col] = mapping_info

    return column_mapping


def convert_dense_to_sparse(
    df: pd.DataFrame,
    id_column: str,
    column_mapping: Dict[str, Dict[str, Union[str, bool]]],
    mapping_df: Optional[pd.DataFrame] = None,
) -> Dict[str, pd.DataFrame]:
    """Convert dense format to sparse format grouped by target table"""
    table_dataframes: Dict[str, List[pd.DataFrame]] = {}

    for col, mapping in column_mapping.items():
        if (
            col not in df.columns
            or type(mapping["table"]) is not str
            or type(mapping["property_name"]) is not str
        ):
            continue

        table_name = mapping["table"]
        property_name = mapping["property_name"]

        # Skip rows with null/nan values
        valid_data = df[[id_column, col]].dropna()

        if len(valid_data) == 0:
            continue

        # Create sparse format dataframe based on table type
        if table_name == "datasource_association_score":
            # Special handling for datasource_association_score table
            sparse_df = pd.DataFrame(
                {
                    "gene_id": valid_data[id_column],
                    "datasource_id": mapping.get("datasource_id", property_name),
                    "score": valid_data[col].astype(float),
                }
            )

            # Add disease_id and gene_name
            if mapping.get("disease_id"):
                sparse_df["disease_id"] = mapping["disease_id"]

            if mapping_df is not None:
                sparse_df = sparse_df.merge(mapping_df, on="gene_id", how="left")
                sparse_df["gene_name"] = sparse_df["gene_name"].fillna("")
            else:
                sparse_df["gene_name"] = ""
        elif table_name == "overall_association_score":
            # Special handling for overall_association_score table (no property_name column)
            sparse_df = pd.DataFrame(
                {
                    "gene_id": valid_data[id_column],
                    "score": valid_data[col].astype(float),
                }
            )

            # Add disease_id
            if mapping.get("disease_id"):
                sparse_df["disease_id"] = mapping["disease_id"]

            # Add gene_name
            if mapping_df is not None:
                sparse_df = sparse_df.merge(mapping_df, on="gene_id", how="left")
                sparse_df["gene_name"] = sparse_df["gene_name"].fillna("")
            else:
                sparse_df["gene_name"] = ""
        else:
            # Standard sparse format for other tables (with property_name)
            if table_name == "pathway":
                valid_data = valid_data[valid_data[col] == 1]

                sparse_df = pd.DataFrame(
                    {
                        "gene_id": valid_data[id_column],
                        "property_name": property_name,
                        "score": valid_data[col].astype(int),
                    }
                )
            else:
                sparse_df = pd.DataFrame(
                    {
                        "gene_id": valid_data[id_column],
                        "property_name": property_name,
                        "score": valid_data[col].astype(float),
                    }
                )

            # Add disease_id for disease-dependent tables
            if mapping["requires_disease"] and mapping.get("disease_id"):
                sparse_df["disease_id"] = mapping["disease_id"]

        # Append to the appropriate table dataframe list
        if table_name not in table_dataframes:
            table_dataframes[table_name] = []
        table_dataframes[table_name].append(sparse_df)

    # Concatenate dataframes for non-target_prioritization tables
    final_dataframes: Dict[str, pd.DataFrame] = {}
    for table_name, data in table_dataframes.items():
        if data:  # If we have data
            final_dataframes[table_name] = pd.concat(data, ignore_index=True)

    return final_dataframes


def process_sparse_format(
    df: pd.DataFrame,
    id_column: str,
    table_name: str,
    mapping_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Process data already in sparse format"""
    processed_df = df.copy()

    # Ensure required columns exist
    if "gene_id" not in processed_df.columns:
        processed_df = processed_df.rename(columns={id_column: "gene_id"})

    # Add disease_id if missing
    if table_name in ["overall_association_score", "datasource_association_score"]:
        if "disease_id" not in processed_df.columns:
            split_parts = processed_df["property_name"].str.split(
                "_OpenTargets_", n=1, expand=True
            )
            if len(split_parts.columns) == 2:
                processed_df["disease_id"] = split_parts[0]
                if table_name == "datasource_association_score":
                    processed_df["datasource_id"] = split_parts[1]
                else:
                    processed_df["property_name"] = split_parts[1]
            else:
                console.print(
                    f"[red]Error: property_name column does not contain expected '_OpenTargets_' pattern for table {table_name}, when disease_id column is not available[/red]"
                )
                sys.exit(1)
        # Drop the old column (not needed for overall_association_score)
        if table_name == "overall_association_score":
            processed_df = processed_df.drop(columns=["property_name"], errors="ignore")
        else:
            if "datasource_id" not in processed_df.columns:
                processed_df["datasource_id"] = (
                    processed_df["property_name"].str.split("_OpenTargets_").str[-1]
                )

        if "gene_name" not in processed_df.columns:
            if mapping_df is None:
                console.print(
                    f"[red]Error: gene_name column is required for table {table_name} when mapping file is not provided[/red]"
                )
                sys.exit(1)
            # Add gene_name from mapping_df
            processed_df = processed_df.merge(mapping_df, on="gene_id", how="left")
            processed_df["gene_name"] = processed_df["gene_name"].fillna("")

    if table_name == "differential_expression":
        if "disease_id" not in processed_df.columns:
            # Split once and assign both parts efficiently
            split_parts = processed_df["property_name"].str.split(
                "_DEG_", n=1, expand=True
            )
            if len(split_parts.columns) == 2:
                processed_df["disease_id"] = split_parts[0]
                processed_df["property_name"] = split_parts[1]
            else:
                console.print(
                    f"[red]Error: property_name column does not contain expected '_DEG_' pattern for {table_name} table, when disease_id column is not available[/red]"
                )
                sys.exit(1)
        else:
            # Ensure property_name is correctly set
            processed_df["property_name"] = (
                processed_df["property_name"].str.split("_DEG_").str[-1]
            )

    # Ensure score column is float
    if "score" in processed_df.columns:
        processed_df["score"] = pd.to_numeric(processed_df["score"], errors="coerce")

    return processed_df.dropna()


def interactive_column_mapping(
    columns: List[str],
) -> Dict[str, Dict[str, Union[str, bool]]]:
    """Interactive column mapping for unrecognized columns"""
    mapping = {}
    available_tables = list(set(TABLE_MAPPINGS.values())) + [
        "differential_expression",
        "overall_association_score",
        "datasource_association_score",
    ]

    for col in columns:
        questions = [
            inquirer.List(
                "table",
                message=f"Which table should column '{col}' map to?",
                choices=["Skip this column"] + available_tables,
            ),
        ]

        answers = inquirer.prompt(questions)
        if answers and answers.get("table") != "Skip this column":
            table_choice = answers["table"]

            # For overall_association_score, don't ask for property_name
            if table_choice == "overall_association_score":
                mapping[col] = {
                    "table": table_choice,
                    "property_name": None,  # No property_name for this table
                    "requires_disease": True,
                    "requires_mapping": True,
                }
            elif table_choice == "datasource_association_score":
                # Ask for datasource_id
                datasource_questions = [
                    inquirer.Text(
                        "datasource_id",
                        message=f"What should be the datasource_id for '{col}'?",
                        default=col,
                    ),
                ]
                datasource_answers = inquirer.prompt(datasource_questions)

                if datasource_answers:
                    mapping[col] = {
                        "table": table_choice,
                        "property_name": None,
                        "datasource_id": datasource_answers["datasource_id"],
                        "requires_disease": True,
                        "requires_mapping": True,
                    }
            else:
                # Ask for property name for other tables
                prop_questions = [
                    inquirer.Text(
                        "property_name",
                        message=f"What should be the property_name for '{col}'?",
                        default=col,
                    ),
                ]
                prop_answers = inquirer.prompt(prop_questions)

                if prop_answers:
                    mapping[col] = {
                        "table": table_choice,
                        "property_name": prop_answers["property_name"],
                        "requires_disease": table_choice in ["differential_expression"],
                        "requires_mapping": False,
                    }

    return mapping


# CLI Commands
@click.group()
@click.version_option(version="1.0.0")
def cli():
    """TBEP CLI for Database manipulation"""
    pass


@cli.group()
def universal():
    """Handles properties of the nodes in the graph database"""
    pass


@cli.group()
def network():
    """Handles network related operations"""
    pass


@cli.group()
def test():
    """Test service connection"""
    pass


@cli.command()
def print_examples():
    """Print all example usage patterns"""
    from rich.syntax import Syntax
    from rich.panel import Panel
    from os.path import basename

    console = Console()

    # Example 1: Basic usage with dense format data
    EXAMPLE_DENSE_USAGE = f"""
    # Seed dense format data with auto-detection
    python {basename(__file__)} universal seed \\
        --file data/gene_expression_data.csv \\
        --clickhouse-host localhost \\
        --clickhouse-port 8123 \\
        --clickhouse-database default \\
        --clickhouse-username default \\
        --format auto \\
        --interactive
    """

    # Example 2: Sparse format data
    EXAMPLE_SPARSE_USAGE = f"""
    # Seed sparse format data to specific table
    python {basename(__file__)} universal seed \\
        --file data/pathway_scores.csv \\
        --clickhouse-host localhost \\
        --clickhouse-port 8123 \\
        --clickhouse-database default \\
        --clickhouse-username default \\
        --format sparse \\
        --table pathway \\
        --id-column gene_id \\
    """

    # Example 3: Target prioritization factors (wide format)
    EXAMPLE_TARGET_PRIORITIZATION_USAGE = f"""
    # Seed target prioritization factors
    python {basename(__file__)} universal seed \\
        --file data/target_prioritization.csv \\
        --clickhouse-host localhost \\
        --clickhouse-port 8123 \\
        --clickhouse-database default \\
        --clickhouse-username default \\
        --format dense \\
        --id-column gene_id \\
        --interactive
    """

    # Example 4: Disease-specific differential expression
    EXAMPLE_DISEASE_SPECIFIC_USAGE = f"""
    # Seed disease-specific differential expression data
    python {basename(__file__)} universal seed \\
        --file data/alzheimer_deg.csv \\
        --clickhouse-host localhost \\
        --clickhouse-port 8123 \\
        --clickhouse-database default \\
        --clickhouse-username default \\
        --format dense \\
        --interactive
    """

    # Example 5: Non-interactive mode
    EXAMPLE_NON_INTERACTIVE_USAGE = f"""
    # Seed data in non-interactive mode (all parameters specified)
    python {basename(__file__)} universal seed \\
        --file data/druggability_scores.csv \\
        --clickhouse-host clickhouse-server.company.com \\
        --clickhouse-port 8123 \\
        --clickhouse-database default \\
        --clickhouse-username seeder_user \\
        --clickhouse-password "secure_password" \\
        --format sparse \\
        --table druggability \\
        --id-column gene_id \\
        --no-interactive \\
    """

    # Example 6: Network seeding
    EXAMPLE_NETWORK_SEED = f"""
    # Seed gene interaction network data
    python {basename(__file__)} network seed \
        --file data/network_interactions.csv \
        --neo4j-uri bolt://localhost:7687 \
        --neo4j-database tbep \
        --neo4j-username neo4j \
        --interaction-type PPI
    """

    # Example 7: Test ClickHouse connection
    EXAMPLE_TEST_CONNECTION = f"""
    # Test ClickHouse connection
    python {basename(__file__)} test clickhouse \
        --clickhouse-host localhost \
        --clickhouse-port 8123 \
        --clickhouse-database default \
        --clickhouse-username default
    """

    # Example 8: Verify gene reference data
    EXAMPLE_VERIFY = f"""
    # Verify universal dataset against reference genome
    python {basename(__file__)} verify \
        --reference-genome data/reference_genome.csv \
        --input-file data/universal_input.csv \
        --output-file data/universal_verified.csv \
        --file-type universal
    """

    examples = [
        ("Dense Format Data (Auto-detection)", EXAMPLE_DENSE_USAGE),
        ("Sparse Format Data", EXAMPLE_SPARSE_USAGE),
        ("Target Prioritization Factors", EXAMPLE_TARGET_PRIORITIZATION_USAGE),
        ("Disease-Specific Data", EXAMPLE_DISEASE_SPECIFIC_USAGE),
        ("Non-Interactive Mode", EXAMPLE_NON_INTERACTIVE_USAGE),
        ("Network Interactions", EXAMPLE_NETWORK_SEED),
        ("Test ClickHouse Connection", EXAMPLE_TEST_CONNECTION),
        ("Verify Universal Dataset", EXAMPLE_VERIFY),
    ]

    console.print("[bold blue]ClickHouse Seeder CLI - Usage Examples[/bold blue]\n")

    for title, example in examples:
        syntax = Syntax(example.strip(), "bash", theme="monokai", line_numbers=False)
        panel = Panel(
            syntax, title=f"[bold green]{title}[/bold green]", border_style="blue"
        )
        console.print(panel)
        console.print()


@network.command("seed")
@click.option(
    "--file", "-f", type=click.Path(exists=True), prompt=True, help="CSV/TSV file path"
)
@click.option("--neo4j-uri", "-nU", default="bolt://localhost:7687", help="Neo4j URI")
@click.option("--neo4j-database", "-nd", default="tbep", help="Neo4j database")
@click.option("--neo4j-username", "-nu", default="neo4j", help="Neo4j username")
@click.option(
    "--neo4j-password", "-nP", prompt=True, hide_input=True, help="Neo4j password"
)
@click.option("--id-type", "-it", help="ID type (choices: ENSEMBL-ID, HGNC-Symbol)")
@click.option(
    "--interaction-type",
    "-itp",
    prompt=True,
    help="Interaction type (default: physical)",
)
def network_seed(
    file: str,
    neo4j_uri: str,
    neo4j_database: str,
    neo4j_username: str,
    neo4j_password: str,
    id_type: str,
    interaction_type: LiteralString,
):
    console.print(
        "[yellow]Make sure to not enter header names in CSV/TSV file[/yellow]"
    )
    console.print(
        "[blue]'1st ENSG Gene ID,2nd ENSG Gene ID,Score' should be the format of CSV/TSV file[/blue]"
    )

    ID_TYPE = ["ENSEMBL-ID", "HGNC-Symbol"]
    id_type = id_type.upper().replace(" ", "-")

    interaction_type = interaction_type.upper().replace(" ", "_")
    allowed_interaction_types = ["PPI", "FUN_PPI", "BIO_GRID", "INT_ACT", "STRING"]
    if interaction_type not in allowed_interaction_types:
        console.print(
            f"[red]Error: Interaction type must be one of {', '.join(allowed_interaction_types)}[/red]"
        )
        sys.exit(0)

    interaction_type = "PPI" if interaction_type == "STRING" else interaction_type

    console.print(f"[blue]Loading CSV/TSV file: {file}[/blue]")
    try:
        # Determine separator based on file extension
        separator = (
            "\t" if file.endswith((".tsv", ".tsv.gz", ".tsv.xz", ".tsv.bz2 ")) else ","
        )
        df = pd.read_csv(file, sep=separator, header=None)

        if not id_type:
            # We'll infer ID type based on row content if rows look like ENSG IDs
            sample_value = str(df.iloc[0, 0])
            if sample_value.startswith("ENSG"):
                id_type = "ENSEMBL-ID"
            else:
                id_type = "HGNC-Symbol"
            console.print(f"[blue]Inferred ID type as: {id_type}[/blue]")
        elif id_type not in ID_TYPE:
            console.print(
                f"[red]Error: ID type must be one of {', '.join(ID_TYPE)}[/red]"
            )
            sys.exit(0)

        console.print(
            f"[green]✓ Loaded {len(df)} rows, {len(df.columns)} columns[/green]"
        )
        df.to_csv("interaction_file_temp.csv", index=False, header=False)
    except Exception as e:
        console.print(f"[red]Failed to load CSV/TSV: {e}[/red]")
        sys.exit(1)

    seeder = Neo4jSeeder(neo4j_uri, neo4j_username, neo4j_password, neo4j_database)
    if not seeder.test_connection():
        console.print("[red]Failed to connect to Neo4j[/red]")
        sys.exit(1)

    console.print("[green]✓ Connected to Neo4j[/green]")

    query = f"""
    LOAD CSV FROM 'file:///interaction_file_temp.csv' AS line
    CALL (line) {{
        MATCH (g1:Gene {{ {"ID" if id_type == "ENSEMBL-ID" else "Gene_name"}: toUpper(line[0]) }})
        MATCH (g2:Gene {{ {"ID" if id_type == "ENSEMBL-ID" else "Gene_name"}: toUpper(line[1]) }})
        MERGE (g1)-[r:$interactionType]->(g2)
        ON CREATE SET r.score = toFloat(line[2])
    }} IN TRANSACTIONS;
    """

    result = seeder.driver.execute_query(
        query, {"interactionType": interaction_type}, database_=neo4j_database
    )

    console.print(
        f"[green]✓ Time taken: {result.summary.result_available_after} ms[/green]"
    )
    seeder.close()
    console.print(
        f"[green]✓ Seeded {result.summary.counters.relationships_created} interactions[/green]"
    )

    from os import remove

    remove("interaction_file_temp.csv")


@network.command()
@click.option(
    "--file", "-f", type=click.Path(exists=True), prompt=True, help="CSV/TSV file path"
)
@click.option("--neo4j-uri", "-nU", default="bolt://localhost:7687", help="Neo4j URI")
@click.option("--neo4j-database", "-nd", default="tbep", help="Neo4j database")
@click.option("--neo4j-username", "-nu", default="neo4j", help="Neo4j username")
@click.option(
    "--neo4j-password", "-nP", prompt=True, hide_input=True, help="Neo4j password"
)
def update_reference_genome(
    file: str,
    neo4j_uri: str,
    neo4j_database: str,
    neo4j_username: str,
    neo4j_password: str,
):
    """Update reference genome from CSV/TSV file"""
    console.print(
        "[blue]'HGNC ID,Approved symbol,Approved name,Previous symbols,Alias symbols,Ensembl gene ID,Ensembl ID(supplied by Ensembl)' should be the required header of TSV/CSV file.[/blue]"
    )

    console.print("[blue]Connecting to Neo4j...[/blue]")
    neo4j_seeder = Neo4jSeeder(
        neo4j_uri, neo4j_username, neo4j_password, neo4j_database
    )
    if not neo4j_seeder.test_connection():
        sys.exit(1)
    console.print("[green]✓ Connected to Neo4j successfully[/green]")

    console.print(f"[blue]Loading CSV/TSV file: {file}[/blue]")
    try:
        separator = (
            "\t" if file.endswith((".tsv", ".tsv.gz", ".tsv.xz", ".tsv.bz2 ")) else ","
        )
        df = pd.read_csv(file, sep=separator)
        console.print(
            f"[green]✓ Loaded {len(df)} rows, {len(df.columns)} columns[/green]"
        )

        with neo4j_seeder.driver.session(database=neo4j_database) as session:
            session.run(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (g:Gene) REQUIRE g.ID IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (g:Gene) REQUIRE g.Gene_name IS UNIQUE"
            )
            session.run(
                "CREATE INDEX Gene_name_Gene_Alias IF NOT EXISTS FOR (ga:GeneAlias) ON (ga.Gene_name)"
            )

            record = session.run("MATCH (g:Gene) RETURN count(g) AS count").single()
            new_db = int(record.get("count", 0)) == 0 if record else True

        df.to_csv("data/reference_genome_temp.csv", index=False)
    except Exception as e:
        console.print(f"[red]Failed to load CSV/TSV: {e}[/red]")
        sys.exit(1)

    result = neo4j_seeder.driver.execute_query(
        f"""
        LOAD CSV WITH HEADERS FROM 'file:///data/reference_genome_temp.csv' AS row
        CALL (row) {{
            WITH row, [alias IN split(row.`Alias symbols` + "," + row.`Previous symbols`, ",") | toUpper(trim(alias))] AS aliases
            WHERE row.`Ensembl gene ID` IS NOT NULL OR row.`Ensembl ID(supplied by Ensembl)` IS NOT NULL
            {'UNWIND [symbol IN split(row.`Previous symbols`, ",") | toUpper(trim(symbol))] AS prev_symbol' if not new_db else ""}
            MERGE (g:Gene {{ {"ID: COALESCE(row.`Ensembl ID(supplied by Ensembl)`, row.`Ensembl gene ID`)" if new_db else "`Gene_name`: prev_symbol"} }})
            SET g += {{
                {"`ID`: COALESCE(row.`Ensembl ID(supplied by Ensembl)`, row.`Ensembl gene ID`)," if not new_db else ""}
                `Gene_name`: toUpper(row.`Approved symbol`),
                `Description`: row.`Approved name`,
                `hgnc_gene_id`: row.`HGNC ID`,
                `Aliases`: aliases
            }}
            WITH g, aliases
                UNWIND aliases AS alias
                MERGE (ga:GeneAlias {{ Gene_name: alias }})
                MERGE (ga)-[:ALIAS_OF]->(g)
        }} IN TRANSACTIONS FINISH;
        """,
        database_=neo4j_database,
    )

    console.print("[bold green]✓ Reference genome update completed![/bold green]")
    console.print(
        f"[green]✓ Created/Updated {result.summary.counters.nodes_created} genes and {result.summary.counters.relationships_created} alias relationships[/green]"
    )
    console.print(
        f"[green]✓ Relationships created: {result.summary.counters.relationships_created}[/green]"
    )

    neo4j_seeder.close()
    from os import remove

    remove("data/reference_genome_temp.csv")


@network.command()
@click.option(
    "--file", "-f", type=click.Path(exists=True), prompt=True, help="CSV/TSV file path"
)
@click.option("--neo4j-uri", "-nU", default="bolt://localhost:7687", help="Neo4j URI")
@click.option("--neo4j-database", "-nd", default="tbep", help="Neo4j database")
@click.option("--neo4j-username", "-nu", default="neo4j", help="Neo4j username")
@click.option(
    "--neo4j-password", "-nP", prompt=True, hide_input=True, help="Neo4j password"
)
def update_disease_metadata(
    file: str,
    neo4j_uri: str,
    neo4j_database: str,
    neo4j_username: str,
    neo4j_password: str,
):
    """Update disease metadata from CSV/TSV file"""

    console.print(f"[blue]Loading CSV/TSV file: {file}[/blue]")
    console.print(
        "[blue]'diseaseID,disease name' should be the format of TSV/CSV file without header.[/blue]"
    )
    try:
        separator = (
            "\t" if file.endswith((".tsv", ".tsv.gz", ".tsv.xz", ".tsv.bz2 ")) else ","
        )
        df = pd.read_csv(file, sep=separator, header=None)
        console.print(
            f"[green]✓ Loaded {len(df)} rows, {len(df.columns)} columns[/green]"
        )
        df.to_csv("data/disease_metadata_temp.csv", index=False, header=False)
    except Exception as e:
        console.print(f"[red]Failed to load CSV/TSV: {e}[/red]")
        sys.exit(1)

    console.print("[blue]Connecting to Neo4j...[/blue]")
    neo4j_seeder = Neo4jSeeder(
        neo4j_uri, neo4j_username, neo4j_password, neo4j_database
    )
    if not neo4j_seeder.test_connection():
        sys.exit(1)
    console.print("[green]✓ Connected to Neo4j successfully[/green]")

    with neo4j_seeder.driver.session(database=neo4j_database) as session:
        session.run(
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Disease) REQUIRE d.ID IS UNIQUE"
        )
        session.run("""
            LOAD CSV FROM 'file:///data/disease_metadata_temp.csv' AS row
            CALL (row) {
                MATCH (d:Disease {ID: row[0]})
                SET d.name = row[1]
            } IN TRANSACTIONS;
            """)

        console.print("[green]✓ Successfully updated disease metadata in Neo4j[/green]")
    neo4j_seeder.close()

    from os import remove

    remove("data/disease_metadata_temp.csv")


@network.command()
@click.option(
    "--file", "-f", type=click.Path(exists=True), prompt=True, help="CSV/TSV file path"
)
@click.option("--neo4j-uri", "-nU", default="bolt://localhost:7687", help="Neo4j URI")
@click.option("--neo4j-database", "-nd", default="tbep", help="Neo4j database")
@click.option("--neo4j-username", "-nu", default="neo4j", help="Neo4j username")
@click.option(
    "--neo4j-password", "-nP", prompt=True, hide_input=True, help="Neo4j password"
)
def update_property_metadata(
    file: str,
    neo4j_uri: str,
    neo4j_database: str,
    neo4j_username: str,
    neo4j_password: str,
):
    """Update property metadata from CSV/TSV file"""
    console.print(
        "[blue]'property_name,property_description' should be the required header of TSV/CSV file.[/blue]"
    )

    console.print("[blue]Connecting to Neo4j...[/blue]")
    neo4j_seeder = Neo4jSeeder(
        neo4j_uri, neo4j_username, neo4j_password, neo4j_database
    )
    if not neo4j_seeder.test_connection():
        sys.exit(1)
    console.print("[green]✓ Connected to Neo4j successfully[/green]")

    console.print(f"[blue]Loading CSV/TSV file: {file}[/blue]")
    try:
        separator = (
            "\t" if file.endswith((".tsv", ".tsv.gz", ".tsv.xz", ".tsv.bz2 ")) else ","
        )
        df = pd.read_csv(file, sep=separator)
        if (
            "property_name" not in df.columns
            or "property_description" not in df.columns
        ):
            console.print(
                "[red]File must contain 'property_name' and 'property_description' columns[/red]"
            )
            sys.exit(1)
        console.print(
            f"[green]✓ Loaded {len(df)} rows, {len(df.columns)} columns[/green]"
        )
        df.to_csv("data/property_metadata_temp.csv", index=False)
    except Exception as e:
        console.print(f"[red]Failed to load CSV/TSV: {e}[/red]")
        sys.exit(1)

    result = neo4j_seeder.driver.execute_query(
        """
        LOAD CSV FROM 'file:///data/property_metadata_temp.csv' AS line
        CALL (line) {
            MATCH (p:Property { name: line[0]})
            SET p.description = line[1]
        } IN TRANSACTIONS;
        """,
        database_=neo4j_database,
    )

    console.print(
        f"[green]✓ Property Updated: {result.summary.counters.properties_set}[/green]"
    )
    console.print("[bold green]✓ Property metadata updated successfully![/bold green]")

    from os import remove

    remove("data/property_metadata_temp.csv")


@universal.command()
@click.option(
    "--file", "-f", type=click.Path(exists=True), prompt=True, help="CSV/TSV file path"
)
@click.option("--clickhouse-host", "-ch", default="localhost", help="ClickHouse host")
@click.option("--clickhouse-port", "-cp", default=8123, help="ClickHouse port")
@click.option(
    "--clickhouse-database", "-cd", default="default", help="ClickHouse database"
)
@click.option(
    "--clickhouse-username", "-cu", default="default", help="ClickHouse username"
)
@click.option(
    "--clickhouse-password",
    "-cP",
    prompt=True,
    hide_input=True,
    help="ClickHouse password",
)
@click.option("--neo4j-uri", "-nU", default="bolt://localhost:7687", help="Neo4j URI")
@click.option("--neo4j-username", "-nu", default="neo4j", help="Neo4j username")
@click.option(
    "--neo4j-password", "-nP", prompt=True, hide_input=True, help="Neo4j password"
)
@click.option("--neo4j-database", "-nd", default="tbep", help="Neo4j database")
@click.option(
    "--mapping-file",
    "-m",
    type=click.Path(exists=True),
    help="Gene mapping file (required for OpenTargets data)",
)
@click.option(
    "--format",
    "-fmt",
    type=click.Choice(["auto", "dense", "sparse"]),
    default="auto",
    help="Data format",
)
@click.option("--table", "-t", help="Target table (for sparse format)")
@click.option("--id-column", "-i", default="gene_id", help="ID column name")
@click.option(
    "--interactive/--no-interactive",
    default=True,
    help="Enable interactive mode for column mapping",
)
def seed(
    file: str,
    clickhouse_host: str,
    clickhouse_port: int,
    clickhouse_database: str,
    clickhouse_username: str,
    clickhouse_password: str,
    neo4j_uri: str,
    neo4j_database: str,
    neo4j_username: str,
    neo4j_password: str,
    mapping_file: str,
    format: str,
    table: str,
    id_column: str,
    interactive: bool,
):
    """Seed gene data from CSV/TSV file
    Formats supported: dense, sparse (auto-detect available)

    Dense format: Multiple columns representing different properties/scores
    Example columns: Pathway_<name>, Druggability_<name>, TE_<name>, OT_Prioritization_<name>, <disease>_DEG_<name>, <disease>_OpenTargets_<datasource>

    Sparse format: One row per gene-property combination
    Example columns: gene_id, property_name, score, [disease_id] [gene_name]
    Example rows:
        # pathway table
        gene1, Wnt, 1
        --------------------------------
        # druggability table
        gene1, High, 0.85
        --------------------------------
        # differential_expression table
        gene1, <disease>_DEG_LogFC, 2.5
        OR
        gene1, LogFC, 2.5, <disease>
        --------------------------------
        # overall_association_score table (here, actual property_name column is just placeholder and is not being used)
        gene1, <disease>_OpenTargets_overall_association_score, 0.9, , gene_name
        OR
        gene1, , 0.9, <disease>, gene_name
        --------------------------------
        # datasource_association_score table
        gene1, <disease>_OpenTargets_<datasource>, 0.75, , gene_name
        OR
        gene1, <datasource>, 0.75, <disease>, gene_name

    Note: disease_id is required for disease-dependent tables
    Note: gene_name is required for overall_association_score and datasource_association_score tables
    """

    console.print(
        f"[blue]Connecting to ClickHouse at {clickhouse_host}:{clickhouse_port}...[/blue]"
    )

    clickhouse_seeder = ClickHouseSeeder(
        clickhouse_host,
        clickhouse_port,
        clickhouse_database,
        clickhouse_username,
        clickhouse_password,
    )

    if not clickhouse_seeder.test_connection():
        console.print("[red]Failed to connect to ClickHouse[/red]")
        sys.exit(1)

    console.print("[green]✓ Connected successfully[/green]")

    # Load CSV/TSV file
    console.print(f"[blue]Loading CSV/TSV file: {file}[/blue]")
    try:
        # Determine separator based on file extension
        separator = (
            "\t" if file.endswith((".tsv", ".tsv.gz", ".tsv.xz", ".tsv.bz2 ")) else ","
        )
        df = pd.read_csv(file, sep=separator)
        console.print(
            f"[green]✓ Loaded {len(df)} rows, {len(df.columns)} columns[/green]"
        )
    except Exception as e:
        console.print(f"[red]Failed to load CSV/TSV: {e}[/red]")
        sys.exit(1)

    # Load mapping file if provided
    mapping_df = None
    if mapping_file:
        console.print(f"[blue]Loading gene mapping file: {mapping_file}[/blue]")
        try:
            mapping_df = pd.read_csv(
                mapping_file,
                usecols=["Ensembl ID(supplied by Ensembl)", "Approved symbol"],
            )
            mapping_df = mapping_df.rename(
                columns={
                    "Ensembl ID(supplied by Ensembl)": "gene_id",
                    "Approved symbol": "gene_name",
                }
            )
            console.print(f"[green]✓ Loaded {len(mapping_df)} gene mappings[/green]")
        except Exception as e:
            console.print(f"[red]Failed to load mapping file: {e}[/red]")
            sys.exit(1)

    # Validate ID column
    if id_column not in df.columns:
        console.print(
            f"[yellow]ID column '{id_column}' not found. Using first column '{df.columns[0]}' instead.[/yellow]"
        )
        id_column = df.columns[0]

    # Auto-detect format if needed
    if format == "auto":
        detected_format = detect_format(df, id_column)
        if detected_format == "unknown":
            if interactive:
                questions = [
                    inquirer.List(
                        "format",
                        message="Could not auto-detect format. Please select:",
                        choices=["dense", "sparse"],
                    ),
                ]
                answers = inquirer.prompt(questions)
                if answers:
                    format = answers["format"]
                else:
                    console.print("[red]No format selected[/red]")
                    sys.exit(1)
            else:
                console.print(
                    "[red]Could not auto-detect format. Please specify --format[/red]"
                )
                sys.exit(1)
        else:
            format = detected_format
            console.print(f"[blue]Auto-detected format: {format}[/blue]")

    # Process data based on format
    if format == "dense":
        # Parse column mappings
        data_columns = [col for col in df.columns if col != id_column]
        column_mapping = parse_column_mapping(data_columns)

        # Check if mapping file is required for OpenTargets data
        requires_mapping = any(
            mapping.get("requires_mapping", False)
            for mapping in column_mapping.values()
        )
        if requires_mapping and mapping_df is None:
            console.print(
                "[red]Mapping file is required for OpenTargets data. Please provide --mapping-file option[/red]"
            )
            sys.exit(1)

        # Handle unmapped columns interactively
        unmapped_columns = [col for col in data_columns if col not in column_mapping]
        if unmapped_columns:
            console.print(
                f"[yellow]Found {len(unmapped_columns)} unmapped columns[/yellow]"
            )
            if interactive:
                if not click.confirm("Do you want to map them interactively?"):
                    console.print("[yellow]Skipping unmapped columns[/yellow]")
                else:
                    additional_mapping = interactive_column_mapping(unmapped_columns)
                    for col, mapping in additional_mapping.items():
                        column_mapping[col] = mapping
            else:
                console.print(
                    f"[yellow]Skipping unmapped columns: {unmapped_columns}[/yellow]"
                )

        # Show mapping summary
        col_mapping_table = Table(title="Column Mappings")
        col_mapping_table.add_column("Column", style="cyan")
        col_mapping_table.add_column("Target Table", style="magenta")
        col_mapping_table.add_column("Property Name", style="green")

        for col, mapping in column_mapping.items():
            col_mapping_table.add_row(
                col,
                str(mapping.get("table", "")),
                str(mapping.get("property_name", "")),
            )

        if interactive:
            console.print(col_mapping_table)
            if not click.confirm("Proceed with these mappings?"):
                console.print("[yellow]Operation cancelled[/yellow]")
                sys.exit(0)

        # Convert dense to sparse
        table_dataframes = convert_dense_to_sparse(
            df, id_column, column_mapping, mapping_df
        )

    else:  # sparse format
        if not table:
            if interactive:
                available_tables = list(TABLE_MAPPINGS.values()) + [
                    "differential_expression",
                    "overall_association_score",
                    "target_prioritization_factors",
                ]
                questions = [
                    inquirer.List(
                        "table",
                        message="Select target table:",
                        choices=available_tables,
                    ),
                ]
                answers = inquirer.prompt(questions)
                if answers:
                    table = answers["table"]
                else:
                    console.print("[red]No table selected[/red]")
                    sys.exit(1)
            else:
                console.print(
                    "[red]Target table must be specified for sparse format[/red]"
                )
                sys.exit(1)

        # Process sparse format
        processed_df = process_sparse_format(df, id_column, table, mapping_df)
        table_dataframes = {table: processed_df}

    # Insert data into ClickHouse
    total_inserted = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for table_name, table_df in table_dataframes.items():
            if table_df.empty:
                continue

            task = progress.add_task(
                f"Inserting {len(table_df)} rows into {table_name}...",
                total=len(table_df),
            )

            try:
                clickhouse_seeder.client.insert(
                    table_name,
                    table_df.values.tolist(),
                    column_names=list(table_df.columns),
                    settings={"async_insert": 1, "wait_for_async_insert": 1},
                )
                progress.update(task, advance=len(table_df))

                total_inserted += len(table_df)
                console.print(
                    f"[green]✓ Inserted {len(table_df)} rows into {table_name}[/green]"
                )

            except Exception as e:
                console.print(f"[red]Failed to insert into {table_name}: {e}[/red]")
                continue

    console.print(
        f"\n[bold green]Successfully inserted {total_inserted} total rows![/bold green]"
    )
    clickhouse_seeder.close()

    # Now initialise Neo4j connection and seed property metadata
    console.print("[blue]Connecting to Neo4j...[/blue]")

    neo4j_seeder = Neo4jSeeder(
        neo4j_uri, neo4j_username, neo4j_password, neo4j_database
    )
    if not neo4j_seeder.test_connection():
        sys.exit(1)

    console.print("[green]✓ Connected to Neo4j successfully[/green]")

    common_properties: List[Dict[str, str]] = []
    disease_properties: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    # Seed property metadata for all relevant tables
    for table_name, table_df in table_dataframes.items():
        category = TABLE_CATEGORY_MAPPING.get(table_name, None)
        if table_df.empty or not category:
            continue

        if table_name == "differential_expression":
            for disease in table_df["disease_id"].unique():
                # get all property names for this disease
                props = table_df[table_df["disease_id"] == disease][
                    "property_name"
                ].unique()
                disease_properties[disease].extend(
                    [
                        {
                            "name": prop,
                            "category": "DEG",
                        }
                        for prop in props
                    ]
                )
        elif table_name == "overall_association_score":
            common_properties.append(
                {
                    "name": "Overall_Association Score",
                    "category": category,
                }
            )
        elif table_name == "datasource_association_score":
            common_properties.extend(
                [
                    {
                        "name": ds,
                        "category": category,
                    }
                    for ds in table_df["datasource_id"].unique()
                ]
            )
        else:
            common_properties.extend(
                [
                    {
                        "name": prop,
                        "category": category,
                    }
                    for prop in table_df["property_name"].unique()
                ]
            )

    neo4j_seeder.seed_properties(common_properties, disease_properties)
    console.print("[bold green]✓ Property metadata seeded successfully![/bold green]")

    # Close Neo4j connection
    neo4j_seeder.close()


@universal.command()
@click.option("--clickhouse-host", "-h", default="localhost", help="ClickHouse host")
@click.option("--clickhouse-port", "-p", default=8123, help="ClickHouse port")
@click.option(
    "--clickhouse-database", "-d", default="default", help="ClickHouse database"
)
@click.option(
    "--clickhouse-username", "-u", default="default", help="ClickHouse username"
)
@click.option(
    "--clickhouse-password",
    "-P",
    prompt=True,
    hide_input=True,
    help="ClickHouse password",
)
@click.option("--table", "-t", prompt=True, help="Target table to delete from")
def delete(
    clickhouse_host,
    clickhouse_port,
    clickhouse_database,
    clickhouse_username,
    clickhouse_password,
    table,
):
    """Delete all data from a ClickHouse table"""

    console.print(
        f"[blue]Connecting to ClickHouse at {clickhouse_host}:{clickhouse_port}...[/blue]"
    )
    clickhouse_seeder = ClickHouseSeeder(
        clickhouse_host,
        clickhouse_port,
        clickhouse_database,
        clickhouse_username,
        clickhouse_password,
    )
    if not clickhouse_seeder.test_connection():
        console.print("[red]Failed to connect to ClickHouse[/red]")
        sys.exit(1)

    console.print("[green]✓ Connected successfully[/green]")

    # Confirm deletion
    if not click.confirm(
        f"Are you sure you want to delete all data from table '{table}'? This action cannot be undone."
    ):
        console.print("[yellow]Operation cancelled[/yellow]")
        sys.exit(0)

    try:
        clickhouse_seeder.client.command(f"TRUNCATE TABLE {table}")
        console.print(
            f"[bold green]✓ Successfully deleted all data from table '{table}'[/bold green]"
        )
    except Exception as e:
        console.print(f"[red]Failed to delete data from table '{table}': {e}[/red]")
        sys.exit(1)


@test.command()
@click.option("--clickhouse-host", "-ch", default="localhost", help="ClickHouse host")
@click.option("--clickhouse-port", "-cp", default=8123, help="ClickHouse port")
@click.option(
    "--clickhouse-database", "-cd", default="default", help="ClickHouse database"
)
@click.option(
    "--clickhouse-username", "-cu", default="default", help="ClickHouse username"
)
@click.option(
    "--clickhouse-password",
    "-cP",
    prompt=True,
    hide_input=True,
    help="ClickHouse password",
)
def clickhouse(
    clickhouse_host,
    clickhouse_port,
    clickhouse_database,
    clickhouse_username,
    clickhouse_password,
):
    """Test ClickHouse connection"""

    console.print(
        f"[blue]Testing connection to {clickhouse_host}:{clickhouse_port}/{clickhouse_database}...[/blue]"
    )

    clickhouse_seeder = ClickHouseSeeder(
        clickhouse_host,
        clickhouse_port,
        clickhouse_database,
        clickhouse_username,
        clickhouse_password,
    )
    if not clickhouse_seeder.test_connection():
        console.print("[red]Failed to connect to ClickHouse[/red]")
        sys.exit(1)
    console.print("[bold green]✓ Connection successful![/bold green]")

    # Show available tables
    try:
        if clickhouse_seeder:
            result = clickhouse_seeder.client.query("SHOW TABLES")
            tables = result.result_rows
            if tables:
                table_list = Table(title="Available Tables")
                table_list.add_column("Table Name", style="cyan")
                for table in tables:
                    table_list.add_row(table[0])
                console.print(table_list)
    except Exception as e:
        console.print(f"[yellow]Could not list tables: {e}[/yellow]")


@test.command()
@click.option("--neo4j-uri", "-nU", default="bolt://localhost:7687", help="Neo4j URI")
@click.option("--neo4j-database", "-nd", default="tbep", help="Neo4j database")
@click.option("--neo4j-username", "-nu", default="neo4j", help="Neo4j username")
@click.option(
    "--neo4j-password", "-nP", prompt=True, hide_input=True, help="Neo4j password"
)
def neo4j(neo4j_uri, neo4j_database, neo4j_username, neo4j_password):
    """Test Neo4j connection"""

    console.print(
        f"[blue]Testing connection to {neo4j_uri} (database: {neo4j_database})...[/blue]"
    )
    neo4j_seeder = Neo4jSeeder(
        neo4j_uri, neo4j_username, neo4j_password, neo4j_database
    )
    if neo4j_seeder.test_connection():
        console.print("[bold green]✓ Connection successful![/bold green]")
    else:
        console.print("[bold red]✗ Connection failed![/bold red]")
        sys.exit(1)
    neo4j_seeder.close()


@cli.command()
@click.option(
    "--reference-genome",
    "-ref",
    type=click.Path(exists=True),
    prompt=True,
    help="CSV/TSV file containing reference genome",
)
@click.option(
    "--input-file",
    "-i",
    type=click.Path(exists=True),
    prompt=True,
    help="Input CSV/TSV file to verify",
)
@click.option(
    "--output-file",
    "-o",
    type=click.Path(),
    help="Output CSV/TSV path for the verified file",
)
@click.option(
    "--primary-header",
    default="Ensembl gene ID",
    help="Primary column name in the reference genome",
)
@click.option(
    "--secondary-header",
    default="Ensembl ID(supplied by Ensembl)",
    help="Secondary column name in the reference genome",
)
@click.option(
    "--gene-symbol-header",
    default="Approved symbol",
    help="Gene Symbol column name in the reference genome",
)
@click.option(
    "--file-type",
    "-t",
    type=click.Choice(["universal", "network"], case_sensitive=False),
    prompt=True,
    help="Verification mode",
)
def verify(
    reference_genome: str,
    input_file: str,
    output_file: str,
    primary_header: str,
    secondary_header: str,
    gene_symbol_header: str,
    file_type: str,
):
    if not output_file:
        [basename, extension] = input_file.rsplit(".", 1)
        output_file = f"{basename}_verified.{extension}"

    print(f"[blue]Loading reference genome: {reference_genome}[/blue]")
    try:
        # Determine separator based on file extension
        separator = (
            "\t"
            if reference_genome.endswith((".tsv", ".tsv.gz", ".tsv.xz", ".tsv.bz2"))
            else ","
        )
        ref_df = pd.read_csv(reference_genome, sep=separator)

        # Check if required headers exist
        if (
            primary_header not in ref_df.columns
            and secondary_header not in ref_df.columns
        ):
            print(
                f"[red]Reference genome must contain at least one of the specified headers: '{primary_header}' or '{secondary_header}'[/red]"
            )
            sys.exit(1)

        # Extract gene IDs from available columns
        available_cols = [
            col for col in [primary_header, secondary_header] if col in ref_df.columns
        ]
        gene_set = set(
            pd.concat(
                [ref_df[col].dropna().astype(str).str.strip() for col in available_cols]
            ).unique()
        )
        gene_set.discard("")

    except Exception as error:
        print(f"[red]Error reading reference genome: {error}[/red]")
        sys.exit(1)

    print(f"[green][bold]✓[/bold] GeneID set size: {len(gene_set)}[/green]")

    print(f"[blue]Loading input file: {input_file}[/blue]")
    try:
        # Determine separator based on file extension
        separator = (
            "\t"
            if input_file.endswith((".tsv", ".tsv.gz", ".tsv.xz", ".tsv.bz2"))
            else ","
        )
        input_df = pd.read_csv(input_file, sep=separator)

        if file_type == "universal":
            # For universal files, filter based on first column
            first_col = input_df.columns[0]
            mask = input_df[first_col].astype(str).str.strip().isin(gene_set)
            filtered_df = input_df[mask]
        else:
            if not str(input_df.iloc[0, 0]).startswith("ENSG"):
                if gene_symbol_header not in ref_df.columns:
                    print(
                        f"[red]Reference genome must contain '{gene_symbol_header}' column for network file verification[/red]"
                    )
                    sys.exit(1)
                gene_set = set(
                    ref_df[gene_symbol_header].dropna().astype(str).str.strip().unique()
                )
                gene_set.discard("")

            # For network files, filter based on first two columns
            if len(input_df.columns) < 2:
                print("[red]Network files must have at least 2 columns[/red]")
                sys.exit(1)

            first_col, second_col = input_df.columns[:2]
            mask = input_df[first_col].astype(str).str.strip().isin(
                gene_set
            ) & input_df[second_col].astype(str).str.strip().isin(gene_set)
            filtered_df = input_df[mask]

        # Save filtered data
        output_separator = (
            "\t"
            if output_file.endswith((".tsv", ".tsv.gz", ".tsv.xz", ".tsv.bz2"))
            else ","
        )
        filtered_df.to_csv(output_file, sep=output_separator, index=False)

    except Exception as error:
        print(f"[red]Failed to verify CSV: {error}[/red]")
        sys.exit(1)

    print("[green][bold]✓[/bold] CSV verified successfully.[/green]")
    print(f"[green][bold]✓[/bold] Total filtered rows: {len(filtered_df)}[/green]")
    print(f"[green][bold]✓[/bold] Output file: {output_file}[/green]")


if __name__ == "__main__":
    cli()
