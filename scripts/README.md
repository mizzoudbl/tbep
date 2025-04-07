> **NOTE:** It is a markdown file so it can be rendered in a markdown viewer. For VSCode, you can press `Ctrl+Shift+V` to open the markdown preview.

# Important Instructions

- Before running any script, make sure to have the necessary dependencies installed by running `npm install` or `pnpm install`(used pnpm here for building the scripts) in this directory.

- For using python scripts, make sure to install necessary dependencies using `pip install -r requirements.txt` ([requirements.txt](./requirements.txt)). Here, is the list of dependencies:

  - `pandas`
  - `fastparquet`

- For [gene-universal-seed](./gene-universal-seed.js) to work, you need to have the csv file inside this scripts directory as this is linked to docker volume of the neo4j database.

- Scripts can either be run using `node <script-name>` or `npm run <script-name>` which have CLI behavior and interactive prompts behavior respectively. Use `node <filename> -h` to see the help message.

- These scripts are primarily designed to be run in a local/server environment and not in a remote environment, i.e. data can't be ingested from a remote location. Though it can be deleted from a remote location.

# Updating OpenTargets Data

## Target Prioritization Scores

Run this automation script:

* [bash](./automation/tps-automation.sh)
* [powershell](./automation/tps-automation.ps1)