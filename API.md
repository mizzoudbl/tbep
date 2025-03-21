# API Documentation

## GraphQL Endpoints

**GraphQL Endpoint URL:** `https://pdnet.missouri.edu/graphql`

### 1. **Fetch Gene Interactions Network**

> [!NOTE]
> This response only contains baseline network. For getting universal data, you need to request for it lazily. For headers, use [get headers endpoint](#3-get-headers).

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
    }
  }
}
```

- **Example Request Body**

```json
{
  "query": "query GetGeneInteractions($input: InteractionInput!, $order: Int!) { getGeneInteractions(input: $input, order: $order) { genes { ID Gene_name Description } graphName links { gene1 gene2 score } } }",
  "variables": {
    "input": {
      "geneIDs": ["BRCA1", "TP53"],
      "interactionType": "PPI",
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
    "getGeneInteractions": [
      {
        "genes": [
          {
            "ID": "BRCA1",
            "Gene_name": "BRCA1",
            "Description": "Breast cancer type 1 susceptibility protein"
          }
        ],
        "graphName":"8ccf297799d6466a1e465b7f03457f5c7f09ec052eab8c6e4bd642bd6f1bb48e",
        "links": [
          {
            "gene1": "BRCA1",
            "gene2": "TP53",
            "score": 0.95
          }
        ]
      }
    ]
  }
}

```

### 2. **Get Universal Data (Lazily)**

- **Query**

```graphql
query GetGenes($config: [DataRequired!], $geneIDs: [String!]!) {
  genes(config: $config, geneIDs: $geneIDs) {
    ID # ensembl ID (ENSG ID) of gene
    Input # input gene ID (that was requested)
    Gene_name # HGNC gene name
    Description # gene description
    Aliases # array of gene aliases
    common # JSON object containing common property values (if requested)
    disease # JSON object containing disease-specific property values (if requested)
  }
}
```

- **Example Request Body**

```json
{
  "query": "query GetGenes($config: [DataRequired!], $geneIDs: [String!]!) { genes(config: $config, geneIDs: $geneIDs) { ID Gene_name Description common disease } }",
  "variables": {
    "config": [
      {
        "disease": "PSP",
        "properties": ["GDA_Score_opentargets_overall_association_score"]
      },
      {
        "properties": ["pathway_Oxidative Stress Induced Senescence"]
      }
    ],
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
        "ID": "BRCA1",
        "Gene_name": "BRCA1",
        "Description": "Breast cancer type 1 susceptibility protein",
        "Aliases": "BRCA1, BRCC1, BROVCA1, FANCS, IRIS, PNCA4, PPP1R53, PSCP, RNF53",
        "disease": {
          "GDA_Score_opentargets_overall_association_score": 0.5
        },
        "common": {
          "pathway_Oxidative Stress Induced Senescence": 1
        }
      },
      ...
    ]
  }
}

```

### 3. **Get Headers**

> [!NOTE]
> The common headers are the same for all diseases, while the disease headers are specific to the disease. So, when changing the disease map, the common headers will remain the same, so you can omit that part in GraphQL query which reduces the amount of data transferred over the network. 

- **Query**

```graphql
query GetHeaders($disease: String) {
  headers(disease: "ALS") {
    common {
      name
      description
    }
    disease {
      name
      description
    }
  }
}
```

- **Example Request Body**

```json
{
  "query": "query GetHeaders($disease: String!) { headers(disease: $disease) { common { name description } disease { name description } } }",
  "variables": {
    "disease": "PSP"
  }
}
```

```json
{
 "data": {
  "headers": {
       "common": [
        {
          "name": "Database_Mendelian_GenCC_ALS",
          "description": "Association score from Mendelian GenCC ALS"
        },
        {
          "name": "Druggability_Score_drugnome_small molecule",
          "description": "Druggability score from DrugNome for small molecules"
        },
        {
          "name": "Pathway_Oxidative Stress Induced Senescence",
          "description": "Pathway score for Oxidative Stress Induced Senescence"
        },
        {
          "name": "TE_appendix",
          "description": "Transcriptomic evidence from appendix"
        }
        ...
      ],
      "disease": [
        {
          "name": "GDA_Score_opentargets_overall_association_score",
          "description": "Overall association score from OpenTargets"
        },
        {
          "name": "GDA_Score_opentargets_uniprot_variants",
          "description": "Association score from OpenTargets based on UniProt variants"
        },
        {
          "name": "GDA_Score_opentargets_eva",
          "description": "Association score from OpenTargets based on EVA"
        },
        {
          "name": "GDA_Score_opentargets_clingen",
          "description": "Association score from OpenTargets based on ClinGen"
        }
        ...
      ],
    }
  }
}
```

### 4. **Get Disease List**

- **Query**

```graphql
query GetDiseaseList {
  diseases {
    name
    description
  }
}
```

- **Example Request Body**

```json
{
  "query": "query GetDiseaseList { diseases { name description } }"
}
```

- **Example Response:**

```json
{
  "data": {
    "diseases": [
      {
        "name": "ALS",
        "description": "Amyotrophic Lateral Sclerosis"
      },
      {
        "name": "PSP",
        "description": "Progressive Supranuclear Palsy"
      },
      ...
    ]
  }
}
```

## REST Endpoints

### 1. **Leiden Algorithm**

- **Base Endpoint:** `https://pdnet.missouri.edu/algorithm`

- **Request**

```http
GET /leiden?graphName=8ccf297799d6466a1e465b7f03457f5c7f09ec052eab8c6e4bd642bd6f1bb48e&resolution=1.0&weighted=true&minCommunitySize=1
```

- **Response**

```json
{
  "1": {
    "name": "Community 1",
    "genes": [
      "ENSG00000204843",
      "ENSG00000172071"
    ],
    "color": "#df2020"
  },
  "2": {
    "name": "Community 2",
    "genes": [
      "ENSG00000135823"
    ],
    "color": "#20df58"
  },
  "3": {
    "name": "Community 3",
    "genes": [
      "ENSG00000168314"
    ],
    "color": "#8f20df"
  },
  "5": {
    "name": "Community 4",
    "genes": [
      "ENSG00000186868",
      "ENSG00000188906"
    ],
    "color": "#df2020"
  }
}
```

### 2. **GSEA Analysis**

- **Base Endpoint:** `https://pdnet.missouri.edu`

- **Request**

```http
GET /gsea?gene_list=BRCA1,TP53
```

OR

```http
POST /gsea
Content-Type: application/json

["SYN","MAPT","ABO","LRKK2"]
```

- **Response**

```json
[
    {
        "Gene_set": "KEGG_pathways of neurodegeneration - multiple diseases",
        "Overlap": "3/479",
        "P-value": "1.37e-05",
        "Adjusted P-value": "6.13e-02",
        "Odds Ratio": "41.75",
        "Combined Score": "203.12",
        "Genes": "LRRK2,MAPT,DCTN1"
    },
    {
        "Gene_set": "KEGG_Parkinson disease",
        "Overlap": "2/267",
        "P-value": "5.28e-04",
        "Adjusted P-value": "5.16e-02",
        "Odds Ratio": "49.94",
        "Combined Score": "163.66",
        "Genes": "LRRK2,MAPT"
    },
    {
        "Gene_set": "Reactome_PTK6 promotes HIF1A stabilization",
        "Overlap": "1/7",
        "P-value": "1.05e-03",
        "Adjusted P-value": "6.40e-02",
        "Odds Ratio": "952.38",
        "Combined Score": "2837.09",
        "Genes": "LRRK2"
    }
]
```

### 3. **LLM Chatbot**

- **Base Endpoint:** `https://pdnet.missouri.edu/llm`

#### Initialize Chat Stream

- **Request**

```http
POST /chat
Content-Type: application/json

{
  "question": "What is the function of the BRCA1 gene?"
}
```

- **Response**

```json
{
  "streamID": "1633024800000"
}
```

#### Stream Chat Response

- **Request**

```http
GET /stream?sid=1633024800000
Accept: text/event-stream
```

- **Response**

```text
data: The BRCA1 gene provides instructions for making a protein that is directly involved in the repair of damaged DNA.
```