# API Documentation

## GraphQL Endpoints

**GraphQL Endpoint URL:** `https://tbep.missouri.edu/graphql`

### 1. **Fetch Gene Interactions Network**

> [!NOTE]
> This response contains the gene interaction network. For getting additional gene properties, you need to request them lazily using the `geneProperties` query. For available headers/properties, use the [get headers endpoint](#3-get-headers).

- **Query**

```graphql
query GetGeneInteractions($input: InteractionInput!, $order: Int!) {
  getGeneInteractions(input: $input, order: $order) {
    genes {
      ID # ensembl ID (ENSG ID) of gene
      Gene_name # HGNC gene name
      Description # gene description
    }
    graphName # unique identifier for the graph
    links {
      gene1 # ensembl ID (ENSG ID) of gene1
      gene2 # ensembl ID (ENSG ID) of gene2
      score # interaction score
      typeScores # JSON object with score breakdown by interaction type
    }
    averageClusteringCoefficient # network metric
  }
}
```

- **Example Request Body**

```json
{
  "query": "query GetGeneInteractions($input: InteractionInput!, $order: Int!) { getGeneInteractions(input: $input, order: $order) { genes { ID Gene_name Description } graphName links { gene1 gene2 score typeScores } averageClusteringCoefficient } }",
  "variables": {
    "input": {
      "geneIDs": ["BRCA1", "TP53"],
      "interactionType": ["PPI"],
      "minScore": 0.8
    },
    "order": 1
  }
}
```

- **Example Response:**

```json
{
  "data": {
    "getGeneInteractions": {
      "genes": [
        {
          "ID": "ENSG00000012048",
          "Gene_name": "BRCA1",
          "Description": "Breast cancer type 1 susceptibility protein"
        },
        {
          "ID": "ENSG00000141510",
          "Gene_name": "TP53",
          "Description": "Tumor protein p53"
        }
      ],
      "graphName": "8ccf297799d6466a1e465b7f03457f5c7f09ec052eab8c6e4bd642bd6f1bb48e",
      "links": [
        {
          "gene1": "ENSG00000012048",
          "gene2": "ENSG00000141510",
          "score": 0.95,
          "typeScores": {
            "PPI": 0.95
          }
        }
      ],
      "averageClusteringCoefficient": 0.65
    }
  }
}
```

### 2. **Get Gene Metadata**

- **Query**

```graphql
query GetGenes($geneIDs: [String!]!) {
  genes(geneIDs: $geneIDs) {
    ID # ensembl ID (ENSG ID) of gene
    Input # input gene ID that was requested
    Gene_name # HGNC gene name
    Description # gene description
    Aliases # gene aliases
    hgnc_gene_id # HGNC gene ID
  }
}
```

- **Example Request Body**

```json
{
  "query": "query GetGenes($geneIDs: [String!]!) { genes(geneIDs: $geneIDs) { ID Input Gene_name Description Aliases hgnc_gene_id } }",
  "variables": {
    "geneIDs": ["BRCA1", "TP53"]
  }
}
```

- **Example Response:**

```json
{
  "data": {
    "genes": [
      {
        "ID": "ENSG00000012048",
        "Input": "BRCA1",
        "Gene_name": "BRCA1",
        "Description": "Breast cancer type 1 susceptibility protein",
        "Aliases": "BRCA1, BRCC1, BROVCA1, FANCS, IRIS, PNCA4, PPP1R53, PSCP, RNF53",
        "hgnc_gene_id": "HGNC:1100"
      },
      {
        "ID": "ENSG00000141510",
        "Input": "TP53",
        "Gene_name": "TP53",
        "Description": "Tumor protein p53",
        "Aliases": "TP53, P53, TRP53, BCC7, LFS1",
        "hgnc_gene_id": "HGNC:11998"
      }
    ]
  }
}
```

### 3. **Get Gene Properties**

- **Query**

```graphql
query GetGeneProperties($geneIds: [String!]!, $config: [DataRequired!]!) {
  geneProperties(geneIds: $geneIds, config: $config) {
    ID # ensembl ID (ENSG ID) of gene
    data {
      key # property name
      score # property value
      category # property category
      diseaseId # disease ID (if disease-specific)
    }
  }
}
```

- **Available Categories:**

  - `DIFFERENTIAL_EXPRESSION` (DEG)
  - `OPEN_TARGETS` (OpenTargets)
  - `OT_PRIORITIZATION` (OT_Prioritization)
  - `PATHWAY`
  - `DRUGGABILITY`
  - `TISSUE_EXPRESSION` (TE)

- **Example Request Body**

```json
{
  "query": "query GetGeneProperties($geneIds: [String!]!, $config: [DataRequired!]!) { geneProperties(geneIds: $geneIds, config: $config) { ID data { key score category diseaseId } } }",
  "variables": {
    "config": [
      {
        "diseaseId": "PSP",
        "category": "OPEN_TARGETS",
        "properties": ["overall_association_score"]
      },
      {
        "category": "PATHWAY",
        "properties": ["Oxidative Stress Induced Senescence"]
      }
    ],
    "geneIds": ["ENSG00000012048", "ENSG00000141510"]
  }
}
```

- **Example Response:**

```json
{
  "data": {
    "geneProperties": [
      {
        "ID": "ENSG00000012048",
        "data": [
          {
            "key": "overall_association_score",
            "score": 0.5,
            "category": "OPEN_TARGETS",
            "diseaseId": "PSP"
          },
          {
            "key": "Oxidative Stress Induced Senescence",
            "score": 1,
            "category": "PATHWAY",
            "diseaseId": null
          }
        ]
      }
    ]
  }
}
```

### 4. **Get Headers**

> [!NOTE]
> The headers are categorized by type. Each category contains available properties that can be queried using the `geneProperties` endpoint.

- **Query**

```graphql
query GetHeaders($diseaseId: String!) {
  headers(diseaseId: $diseaseId) {
    openTargets {
      name
      description
    }
    differentialExpression {
      name
      description
    }
    druggability {
      name
      description
    }
    pathway {
      name
      description
    }
    tissueSpecificity {
      name
      description
    }
    targetPrioritization {
      name
      description
    }
  }
}
```

- **Example Request Body**

```json
{
  "query": "query GetHeaders($diseaseId: String!) { headers(diseaseId: $diseaseId) { openTargets { name description } pathway { name description } druggability { name description } tissueSpecificity { name description } differentialExpression { name description } targetPrioritization { name description } } }",
  "variables": {
    "diseaseId": "ALS"
  }
}
```

- **Example Response:**

```json
{
  "data": {
    "headers": {
      "openTargets": [
        {
          "name": "overall_association_score",
          "description": "Overall association score from OpenTargets"
        },
        {
          "name": "uniprot_variants",
          "description": "Association score from OpenTargets based on UniProt variants"
        }
      ],
      "pathway": [
        {
          "name": "Oxidative Stress Induced Senescence",
          "description": "Pathway score for Oxidative Stress Induced Senescence"
        }
      ],
      "druggability": [
        {
          "name": "small molecule",
          "description": "Druggability score from DrugNome for small molecules"
        }
      ],
      "tissueSpecificity": [
        {
          "name": "appendix",
          "description": "Tissue expression in appendix"
        }
      ],
      "differentialExpression": [
        {
          "name": "GSE124439",
          "description": "Differential expression from GSE124439"
        }
      ],
      "targetPrioritization": [
        {
          "name": "Genetic Association",
          "description": "Target prioritization based on genetic association"
        }
      ]
    }
  }
}
```

### 5. **Get Top Genes by Disease**

- **Query**

```graphql
query GetTopGenesByDisease($diseaseId: String!, $page: Pagination) {
  topGenesByDisease(diseaseId: $diseaseId, page: $page) {
    gene_name
  }
}
```

- **Example Request Body**

```json
{
  "query": "query GetTopGenesByDisease($diseaseId: String!, $page: Pagination) { topGenesByDisease(diseaseId: $diseaseId, page: $page) { gene_name } }",
  "variables": {
    "diseaseId": "ALS",
    "page": {
      "page": 1,
      "limit": 25
    }
  }
}
```

- **Example Response:**

```json
{
  "data": {
    "topGenesByDisease": [
      {
        "gene_name": "SOD1"
      },
      {
        "gene_name": "TARDBP"
      },
      {
        "gene_name": "FUS"
      }
    ]
  }
}
```

### 6. **Get Target Disease Association Table**

- **Query**

```graphql
query GetTargetDiseaseAssociationTable(
  $geneIds: [String!]!
  $diseaseId: String!
  $orderBy: OrderByEnum
  $page: Pagination
) {
  targetDiseaseAssociationTable(
    geneIds: $geneIds
    diseaseId: $diseaseId
    orderBy: $orderBy
    page: $page
  ) {
    rows {
      target {
        id
        name
        prioritization {
          key
          score
        }
      }
      datasourceScores {
        key
        score
      }
      overall_score
    }
    totalCount
  }
}
```

- **Available OrderBy Options:**

  - `SCORE` (default)
  - `EUROPE_PMC`, `CHEMBL`, `GEL_PANEL_APP`, `GWAS_ASSOCIATIONS`, `IMPC`
  - `CANCER_GENE_CENSUS`, `CLINVAR`, `INTOGEN`, `UNIPROT_CURATED_VARIANTS`
  - `ORPHANET`, `UNIPROT_LITERATURE`, `GENE_BURDEN`, `CLINVAR_SOMATIC`
  - `GENE2PHENOTYPE`, `CLINGEN`, `REACTOME`, `EXPRESSION_ATLAS`
  - `CRISPR_SCREENS`, `GENE_SIGNATURES`, `CANCER_BIOMARKERS`
  - `PROJECT_SCORE`, `SLAPENRICH`, `PROGENY`

- **Example Request Body**

```json
{
  "query": "query GetTargetDiseaseAssociationTable($geneIds: [String!]!, $diseaseId: String!, $orderBy: OrderByEnum, $page: Pagination) { targetDiseaseAssociationTable(geneIds: $geneIds, diseaseId: $diseaseId, orderBy: $orderBy, page: $page) { rows { target { id name prioritization { key score } } datasourceScores { key score } overall_score } totalCount } }",
  "variables": {
    "geneIds": ["ENSG00000012048", "ENSG00000141510"],
    "diseaseId": "ALS",
    "orderBy": "SCORE",
    "page": {
      "page": 1,
      "limit": 25
    }
  }
}
```

- **Example Response:**

```json
{
  "data": {
    "targetDiseaseAssociationTable": {
      "rows": [
        {
          "target": {
            "id": "ENSG00000012048",
            "name": "BRCA1",
            "prioritization": [
              {
                "key": "Genetic Association",
                "score": 0.85
              }
            ]
          },
          "datasourceScores": [
            {
              "key": "Europe PMC",
              "score": 0.75
            },
            {
              "key": "ClinVar",
              "score": 0.9
            }
          ],
          "overall_score": 0.82
        }
      ],
      "totalCount": 2
    }
  }
}
```

## REST Endpoints

### 1. **Health Check**

- **Endpoint:** `GET /`

- **Response**

```text
Welcome to the TBEP API!
```

### 2. **Get Disease List**

- **Endpoint:** `GET /diseases`

- **Response**

```json
[
  {
    "name": "ALS",
    "description": "Amyotrophic Lateral Sclerosis"
  },
  {
    "name": "PSP",
    "description": "Progressive Supranuclear Palsy"
  }
]
```

### 3. **Leiden Community Detection Algorithm**

- **Endpoint:** `GET /algorithm/leiden`

- **Query Parameters:**

  - `graphName` (required): Unique identifier for the graph
  - `resolution` (optional, default: 1.0): Resolution parameter for the Leiden algorithm
  - `weighted` (optional, default: true): Whether to use weighted edges
  - `minCommunitySize` (optional, default: 1): Minimum size for communities

- **Request**

```http
GET /algorithm/leiden?graphName=8ccf297799d6466a1e465b7f03457f5c7f09ec052eab8c6e4bd642bd6f1bb48e&resolution=1.0&weighted=true&minCommunitySize=1
```

- **Response**

```json
{
  "modularity": 0.4321,
  "communities": {
    "1": {
      "name": "Community 1",
      "genes": ["ENSG00000204843", "ENSG00000172071"],
      "color": "#df2020"
    },
    "2": {
      "name": "Community 2",
      "genes": ["ENSG00000135823"],
      "color": "#20df58"
    },
    "3": {
      "name": "Community 3",
      "genes": ["ENSG00000168314"],
      "color": "#8f20df"
    }
  }
}
```

### 4. **Renew Graph Session**

- **Endpoint:** `POST /algorithm/renew-session`

- **Request Body**

```json
{
  "graphName": "8ccf297799d6466a1e465b7f03457f5c7f09ec052eab8c6e4bd642bd6f1bb48e",
  "nodes": ["ENSG00000012048", "ENSG00000141510"],
  "edges": [
    {
      "source": "ENSG00000012048",
      "target": "ENSG00000141510",
      "weight": 0.95
    }
  ]
}
```

- **Response**

HTTP 202 Accepted (if successful)
HTTP 409 Conflict (if graph already exists)

### 5. **GSEA Analysis**

> [!NOTE]
> This endpoint is served by a separate Python service running on port 5000.

- **Endpoint:** `POST /gsea`

- **Request**

```http
POST /gsea
Content-Type: application/json

["SNCA", "MAPT", "APP", "LRRK2"]
```

- **Response**

```json
[
  {
    "Pathway": "KEGG_pathways of neurodegeneration - multiple diseases",
    "Overlap": "3/479",
    "P-value": "1.37e-05",
    "Adjusted P-value": "6.13e-02",
    "Odds Ratio": "41.75",
    "Combined Score": "203.12",
    "Genes": "LRRK2,MAPT,APP"
  },
  {
    "Pathway": "KEGG_Parkinson disease",
    "Overlap": "2/267",
    "P-value": "5.28e-04",
    "Adjusted P-value": "5.16e-02",
    "Odds Ratio": "49.94",
    "Combined Score": "163.66",
    "Genes": "LRRK2,MAPT"
  },
  {
    "Pathway": "Reactome_PTK6 promotes HIF1A stabilization",
    "Overlap": "1/7",
    "P-value": "1.05e-03",
    "Adjusted P-value": "6.40e-02",
    "Odds Ratio": "952.38",
    "Combined Score": "2837.09",
    "Genes": "LRRK2"
  }
]
```

### 6. **LLM Chatbot**

- **Endpoint:** `POST /llm/chat`

- **Request Body**

```json
{
  "model": "openai:gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": "What is the function of the BRCA1 gene?"
    }
  ],
  "sessionId": "optional-session-id",
  "userId": "optional-user-id"
}
```

- **Available Models:**

  - `openai:gpt-4o`
  - `nvidia:meta/llama-3.1-405b-instruct`

- **Response**

The response is a streaming response using Server-Sent Events (SSE). The AI SDK UI Message Stream format is used.

```text
data: {"type":"start"}

data: {"type":"text-start","id":"msg_01357f9de831041a00690e0991c650819fbba6a7f2e35a3fe1"}

data: {"type":"text-delta","id":"msg_01357f9de831041a00690e0991c650819fbba6a7f2e35a3fe1","delta":"Sure"}

data: {"type":"text-delta","id":"msg_01357f9de831041a00690e0991c650819fbba6a7f2e35a3fe1","delta":"!"}

data: {"type":"text-delta","id":"msg_01357f9de831041a00690e0991c650819fbba6a7f2e35a3fe1","delta":" Here"}

data: {"type":"text-delta","id":"msg_01357f9de831041a00690e0991c650819fbba6a7f2e35a3fe1","delta":" is"}

data: {"type":"text-delta","id":"msg_01357f9de831041a00690e0991c650819fbba6a7f2e35a3fe1","delta":" some"}

data: {"type":"text-delta","id":"msg_01357f9de831041a00690e0991c650819fbba6a7f2e35a3fe1","delta":" information"}

data: {"type":"text-end","id":"msg_01357f9de831041a00690e0991c650819fbba6a7f2e35a3fe1"}

data: {"type":"finish"}

data: [DONE]
```

> [!NOTE]
> This endpoint uses rate limiting to prevent abuse. The rate limit is applied based on the client's IP address.
