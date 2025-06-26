from pandas import DataFrame
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from gseapy import enrich

KEGG_FILE_PATH = "./pathway_kegg_gsea.gmt"
REACTOME_FILE_PATH = "./pathway_reactome_gsea.gmt"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tbep.missouri.edu", "https://pdnet.missouri.edu"],
    allow_methods=["POST","GET"],
    allow_headers=["*"],
)


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

    result_df: DataFrame = enrich(
        gene_list, gene_sets=[KEGG_FILE_PATH, REACTOME_FILE_PATH], no_plot=True
    ).results  # type: ignore

    result_df = (
        result_df.sort_values(by="P-value", ascending=True)
        .drop(columns=["Gene_set"])
        .rename(columns={"Term": "Pathway"})
    )

    for col in ["P-value", "Adjusted P-value"]:
        result_df[col] = result_df[col].map("{:.2e}".format)

    for col in ["Odds Ratio", "Combined Score"]:
        result_df[col] = result_df[col].map("{:.2f}".format)

    result_df["Genes"] = result_df["Genes"].str.replace(";", ",")

    return result_df.to_dict(orient="records")


@app.get("/")
def hello_world():
    return "Welcome to TBEP Python API!"

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
