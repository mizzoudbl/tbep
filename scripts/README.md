# Important Instructions

- Before running any script, make sure to have the necessary dependencies installed by running `npm install` or `pnpm install`(used pnpm here for building the scripts) in this directory.

- For [gene-universal-seed](./gene-universal-seed.js) to work, you need to have the csv file in the same directory as the script as well as in the import directory of neo4j/docker container.

- Scripts can either be run using `node <script-name>` or `npm run <script-name>` which have CLI behaviour and interactive prompts behaviour respectively. Use `node <filename> -h` to see the help message.

- These scripts are primarily desgined to be run in a local/server environment and not in a remote environment, i.e. data can't be ingested from a remote location. Though it can be deleted from a remote location.

---

> **NOTE:** It is a markdown file so it can be rendered in a markdown viewer. For VSCode, you can press `Ctrl+Shift+V` to open the markdown preview.
