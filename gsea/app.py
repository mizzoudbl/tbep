from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import math
from scipy.stats import hypergeom

KEGG_FILE_PATH = "pathway_kegg_gsea.csv"
REACTONE_FILE_PATH = "pathway_reactome_gsea.csv"

df_kegg = pd.read_csv(KEGG_FILE_PATH).dropna()
df_reactome = pd.read_csv(REACTONE_FILE_PATH).dropna()

df = pd.concat([df_kegg, df_reactome], ignore_index=True)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST","GET"],
    allow_headers=["*"],
)


def calculate_odds_ratio(
    overlap_count: int, expected_overlap: float, epsilon=1e-10
) -> float:
    """
    Calculate the odds ratio

    Parameters
    ----------
    overlap_count : int
        Number of overlapping genes
    expected_overlap : float
        Expected number of overlapping genes

    Returns
    -------
    odds_ratio : float
        Odds ratio
    """
    if expected_overlap == 0 or overlap_count == 0:
        return 0
    odds_ratio = (overlap_count + epsilon) / (expected_overlap + epsilon)
    return odds_ratio


def calculate_combined_score(p_value: float, odds_ratio: float) -> float:
    """
    Calculate the combined score

    Parameters
    ----------
    p_value : float
        P-value
    odds_ratio : float
        Odds ratio

    Returns
    -------
    combined_score : float
        Combined score
    """

    if p_value == 0 or odds_ratio == 0:
        return 0
    return odds_ratio * -math.log10(p_value)


def check_overlap(genes: list[str], pathway_genes: list[str]) -> list[str]:
    """
    Return those genes where there is an overlap between the gene list and the pathway genes

    Parameters
    ----------
    genes : list[str]
        List of genes
    pathway_genes : list[str]
        List of genes in the pathway

    Returns
    -------
    overlap_genes : list[str]
        List of genes that overlap between the gene list and the pathway genes
    """
    return [gene for gene in genes if gene in pathway_genes]


def calculate_p_value(
    overlap_count: int, pathway_size: int, gene_list_size: int, total_genes: int
) -> float:
    """
    Calculate the p-value using the hypergeometric distribution

    Parameters
    ----------
    overlap_count : int
        Number of overlapping genes
    pathway_size : int
        Number of genes in the pathway
    gene_list_size : int
        Number of genes in the gene list
    total_genes : int
        Total number of genes in the genome

    Returns
    -------
    p_value : float
        P-value calculated using the hypergeometric distribution
    """

    N = total_genes
    M = pathway_size
    n = gene_list_size
    k = overlap_count

    p_value = hypergeom.sf(k - 1, N, M, n)
    return p_value


def benjamini_hochberg_correction(p_values: list[float]) -> list[float]:
    """
    Perform Benjamini-Hochberg correction on the p-values

    Parameters
    ----------
    p_values : list[float]
        List of p-values

    Returns
    -------
    adjusted_p_values : list[float]
        List of adjusted p-values
    """

    m = len(p_values)
    sorted_indices = sorted(range(m), key=lambda i: p_values[i])
    sorted_p_values = [p_values[i] for i in sorted_indices]
    adjusted_p_values: list[float] = [0] * m

    for rank, idx in enumerate(sorted_indices):
        p = sorted_p_values[rank]
        adjusted_p = p * m / (rank + 1)
        adjusted_p_values[idx] = min(adjusted_p, 1.0)

    return adjusted_p_values


def process_pathways(gene_list: list[str], total_genes=20000):
    """
    Process pathways and return the results

    Parameters
    ----------
    gene_list : list
        List of genes
    total_genes : int
        Total number of genes in the genome

    Returns
    -------
    result : list[dict]
        List of dictionaries containing the results

    """

    result: list[dict] = []
    p_values: list[float] = []

    for _, row in df.iterrows():

        gene_set = row.iloc[0]

        pathway_genes = str(row[1]).split(" ")

        overlap_genes = check_overlap(gene_list, pathway_genes)

        if overlap_genes:
            overlap_count = len(overlap_genes)
            pathway_size = len(pathway_genes)
            p_value = calculate_p_value(
                overlap_count, pathway_size, len(gene_list), total_genes
            )
            expected_overlap = (pathway_size / total_genes) * len(gene_list)
            odds_ratio = calculate_odds_ratio(overlap_count, expected_overlap)
            combined_score = calculate_combined_score(p_value, odds_ratio)
            p_values.append(p_value)
            result.append(
                {
                    "Pathway": gene_set,
                    "Overlap": f"{overlap_count}/{pathway_size}",
                    "P-value": p_value,
                    "Adjusted P-value": None,  # Placeholder for now
                    "Odds Ratio": format(odds_ratio, ".2f"),
                    "Combined Score": format(combined_score, ".2f"),
                    "Genes": ",".join(overlap_genes),
                }
            )

    result.sort(key=lambda x: x["P-value"])
    adjusted_p_values = benjamini_hochberg_correction(p_values)

    for i, entry in enumerate(result):
        entry["Adjusted P-value"] = format(adjusted_p_values[i], ".2e")
        entry["P-value"] = format(entry["P-value"], ".2e")
    return result


@app.post("/gsea")
async def gsea(
    gene_list: list[str] = Body(
        ..., title="Gene List", description="Comma-separated list of genes"
    )
):
    """
    Perform Gene Set Enrichment Analysis (GSEA) using pathways

    Parameters
    ----------
    gene_list : str
        Comma-separated list of genes

    Returns
    -------
    result : list[dict]
        List of dictionaries containing the results
    """

    result = process_pathways(gene_list)
    return result

@app.get("/")
def hello_world():
    return "Welcome to TBEP Python API!"

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
