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

* [bash](./automation/tps-automation.sh)
* [powershell](./automation/tps-automation.ps1)

> **NOTE:** Any of the script can be run, but both requires `wget` to be installed in the system.
> To install `wget`:
> ```bash
> # Linux
> sudo apt-get install wget
> ```
> ```powershell
> # Windows
> winget install --id GNU.Wget2
> Set-Alias -Name wget -Value wget2
> ```


# FAQ & Acronyms

- *gos:* Gene OpenTargets Seeding
- *gus:* Gene Universal Seeding
- *gss:* Gene Score Seeding
- *tps:* Target Prioritization Score (from OpenTargets) Seeding
- *rgu:* Reference Genome Update
- *dms:* Disease Mapping Seeding
- *ott/opp:* OpenTargets Pre-processor/Transformation (The format I got from Sameera Mam) (made just for Target Disease Association from OpenTargets, as the data was very sparse and large, A simplified pipeline will be made soon)
- *rgv:* Reference Genome Verification
