import neo4j from "neo4j-driver";
import inquirer from "inquirer";
import chalk from "chalk";
import yargs from "yargs";
import Path from "node:path";
import Papa from "papaparse";
import { createReadStream, createWriteStream } from "node:fs";

const defaultUsername = "neo4j";
const defaultDatabase = "tbep";
const defaultDbUrl = "bolt://localhost:7687";

const argv = yargs(process.argv.slice(2))
  .option("file", {
    alias: "f",
    description: "Specify the CSV file path",
    type: "string",
  })
  .option("dbUrl", {
    alias: "U",
    description: "Specify the database URL",
    type: "string",
  })
  .option("username", {
    alias: "u",
    description: "Specify the database username",
    type: "string",
  })
  .option("password", {
    alias: "p",
    description: "Specify the database password",
    type: "string",
  })
  .option("database", {
    alias: "d",
    description: "Specify the database name",
    type: "string",
  })
  .help()
  .alias("help", "h")
  .version("1.0.0")
  .alias("version", "v")
  .usage(
    chalk.green(
      "Usage: $0 [-f | --file] <filename> [-U | --dbUrl] <url> [-u | --username] <username> [-p | --password] <password> [-d | --database] <database>"
    )
  )
  .example(
    chalk.blue(
      "node $0 -f data.csv -U bolt://localhost:7687 -u neo4j -p password -d tbep"
    )
  )
  .example(chalk.cyan("Update Reference Genome in Neo4j")).argv;

async function promptForDetails(answer) {
  const questions = [
    !answer.file && {
      type: "input",
      name: "file",
      message: "Enter the file path:",
      validate: (input) => {
        input = input?.trim();
        if (Path.extname(input) !== ".csv") {
          return "Please enter a CSV file";
        }
        return true;
      },
    },
    !answer.dbUrl && {
      type: "input",
      name: "dbUrl",
      message: "Enter the database URL:",
      default: defaultDbUrl,
    },
    !answer.username && {
      type: "input",
      name: "username",
      message: "Enter the database username:",
      default: defaultUsername,
    },
    !answer.password && {
      type: "password",
      name: "password",
      message: "Enter the database password:",
      mask: "*",
      required: true,
    },
    !answer.database && {
      type: "input",
      name: "database",
      message: "Enter the database name:",
      default: defaultDatabase,
      required: true,
    },
  ].filter(Boolean);

  return inquirer.prompt(questions);
}

(async () => {
  let { file, dbUrl, username, password, database } = await argv;
  if (!file || !dbUrl || !username || !password || !database) {
    try {
      const answers = await promptForDetails({
        file,
        dbUrl,
        username,
        password,
        database,
      });
      file ||= answers.file;
      dbUrl ||= answers.dbUrl;
      username ||= answers.username;
      password ||= answers.password;
      database ||= answers.database;
    } catch (error) {
      console.info(chalk.blue.bold("[INFO]"), chalk.cyan("Exiting..."));
      process.exit(0);
    }
  }
  if (Path.extname(file) !== ".csv") {
    console.error(chalk.bold("[ERROR]"), "Please enter a CSV file. Exiting...");
    process.exit(1);
  }
  const start = new Date().getTime();

  const geneIDs = new Set();
  Papa.parse(createReadStream(file), {
    header: true,
    step: ({ data }) => {
      const {
        "Ensembl gene ID": geneID,
        "Ensembl ID(supplied by Ensembl)": suppliedID,
      } = data;
      if (suppliedID) geneIDs.add(suppliedID);
      else if (geneID) geneIDs.add(geneID);
    },
  });

  const driver = neo4j.driver(dbUrl, neo4j.auth.basic(username, password));
  const session = driver.session({
    database: database,
  });

  try {
    const res = (
      await session.run("MATCH (g:Gene) RETURN g.ID AS ID")
    ).records.map((record) => record.get("ID"));
    const diffGenes = res.filter((id) => !geneIDs.has(id));
    const diffGenesWriter = createWriteStream("diffGenes.txt");
    diffGenesWriter.write(diffGenes.join("\n"));
    diffGenesWriter.close();

    console.log(chalk.green(chalk.bold("[LOG]"), "Creating constraints..."));
    await session.run(
      "CREATE CONSTRAINT IF NOT EXISTS FOR (g:Gene) REQUIRE g.ID IS UNIQUE"
    );
    await session.run(
      "CREATE CONSTRAINT IF NOT EXISTS FOR (g:Gene) REQUIRE g.Gene_name IS UNIQUE"
    );
    await session.run(
      "CREATE INDEX Gene_name_Gene_Alias IF NOT EXISTS FOR (ga:GeneAlias) ON (ga.Gene_name)"
    );

    console.log(
      chalk.green(
        chalk.bold("[LOG]"),
        `Seeding data in database ${database}...`
      )
    );
    console.log(chalk.green(chalk.bold("[LOG]"), "This will take a while..."));

    const query = `
			LOAD CSV WITH HEADERS FROM '${
        /^https?:\/\//.test(file)
          ? file
          : `file:///${file.replace(/^\.[\\/]+/, "")}`
      }' AS line
			CALL {
				WITH line
				WITH line, [alias IN split(line.\`Alias symbols\`, ",") | toUpper(trim(alias))] AS aliases
				WHERE line.\`Ensembl gene ID\` IS NOT NULL OR line.\`Ensembl ID(supplied by Ensembl)\` IS NOT NULL
				MERGE (g:Gene { ID: COALESCE(line.\`Ensembl ID(supplied by Ensembl)\`, line.\`Ensembl gene ID\`) })
				SET g += {
					\`Gene_name\`: toUpper(line.\`Approved symbol\`),
					\`Description\`: line.\`Approved name\`,
					\`hgnc_gene_id\`: line.\`HGNC ID\`,
					\`Aliases\`: aliases
				}
				WITH g, aliases
					UNWIND aliases AS alias
					MERGE (ga:GeneAlias { Gene_name: alias })
					MERGE (ga)-[:ALIAS_OF]->(g)
			} IN TRANSACTIONS FINISH;
		`;

    const result = await session.run(query);

    console.log(
      chalk.green(
        chalk.bold("[LOG]"),
        `Deleting ${diffGenes.length} unused nodes (was not present in reference genome)...`
      )
    );

    const deleteQuery = `
			MATCH (g:Gene) WHERE g.ID IN $geneIDs 
			CALL {
				WITH g
				DETACH DELETE g
			} IN TRANSACTIONS;
		`;
    await session.run(deleteQuery, { geneIDs: diffGenes });

    const end = new Date().getTime();
    console.log(chalk.green(chalk.bold("[LOG]"), "Data loaded using LOAD CSV"));
    console.log(
      chalk.green(
        chalk.bold("[LOG]"),
        `Nodes Created: ${result.summary.counters.updates().nodesCreated}`
      )
    );
    console.log(
      chalk.green(
        chalk.bold("[LOG]"),
        `Relationship Created: ${
          result.summary.counters.updates().relationshipsCreated
        }`
      )
    );

    console.log(
      chalk.green(
        chalk.bold("[LOG]"),
        `Time taken: ${(end - start) / 1000} seconds`
      )
    );
  } catch (error) {
    console.error(
      chalk.bold("[ERROR]"),
      "Error connecting to database. \nMake sure database is active and database URL/credentials are valid"
    );
    console.debug(chalk.bold("[DEBUG]"), error);
  } finally {
    await session.close();
    await driver.close();
  }
})();
