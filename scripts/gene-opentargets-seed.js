import neo4j from "neo4j-driver";
import inquirer from "inquirer";
import { createReadStream, existsSync, mkdirSync, writeFileSync } from "node:fs";
import yargs from "yargs";
import chalk from "chalk";
import Path from "node:path";
import Papa from "papaparse";

const defaultUsername = "neo4j";
const defaultDatabase = "tbep";
const defaultDbUrl = "bolt://localhost:7687";

// Command-line argument parsing with yargs
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
      "node $0 -f opentargets.csv -U bolt://localhost:7687 -u neo4j -p password -d tbep"
    )
  )
  .example(chalk.cyan("Load opentargets data in Neo4j")).argv;

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
        // Check if the file exists
        if (!existsSync(input)) {
          return "File does not exist in this directory. Please enter a valid file path";
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
      message: "Enter the username: (default: neo4j)",
      default: defaultUsername,
    },
    !answer.password && {
      type: "password",
      name: "password",
      message: "Enter the password:",
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
  console.info(
    chalk.blue.bold("[INFO]"),
    chalk.cyan("Example of CSV file (index is not a column in csv file):")
  );
  console.table([
    {
      node_id: "ENSG00000010671",
      property: "EFO_0000095_OpenTargets_score",
      value: "0.6",
    },
    {
      node_id: "ENSG00000110848",
      property: "EFO_0000095_OpenTargets_score",
      value: "0.3",
    },
  ]);

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
    console.error(
      chalk.bold("[ERROR]"),
      "File should be a CSV file. Exiting..."
    );
    process.exit(1);
  }
  if (!existsSync(file)) {
    console.error(
      chalk.bold("[ERROR]"),
      "File does not exist in this directory. Exiting..."
    );
    process.exit(1);
  }

  const driver = neo4j.driver(dbUrl, neo4j.auth.basic(username, password));
  const session = driver.session({
    database: database,
  });

  const query = `
    LOAD CSV FROM '${/^https?:\/\//.test(file) ? file : `file:///${Path.resolve(file).split("scripts").at(-1).replace(/^\.[\\/]+/, "").replace(/\\/g, "/")}`
    }' AS line
    CALL {
      WITH line
      MATCH (g:Gene { ID: line[0] })
      CALL apoc.create.setProperty(g, line[1], toFloat(line[2])) YIELD node FINISH
    } IN 24 CONCURRENT TRANSACTIONS;
    `.replace(/"/g, "");

  try {
    const secondColumn = await new Promise((resolve) => {
      const result = [];
      Papa.parse(createReadStream(file), {
        dynamicTyping: true,
        skipEmptyLines: true,
        step: (row) => {
          result.push(row.data[1]);
        },
        complete: () => resolve(result.slice(1)),
        error: (error) => {
          console.error(chalk.bold("[ERROR]"), error);
          process.exit(1);
        }
      });
    });

    console.log(chalk.green(chalk.bold("[LOG]"), "This will take a while..."));
    const start = new Date().getTime();
    await session.run(query);

    const properties = secondColumn.reduce((acc, val) => {
      const disease = val.split("_OpenTargets_").at(0);
      if (!acc.has(disease)) acc.set(disease, new Set());
      acc.get(disease).add(val);
      return acc;
    }, {});

    for (const disease of Object.keys(properties)) {
      properties[disease] = Array.from(properties[disease]);
    }

    const diseaseAndHeadersUpdateQuery = `
    UNWIND $map AS disease, headers
    MERGE (d:Disease { ID: disease })
    WITH d, headers
    UNWIND headers AS header
    MERGE (p:Property { name: header })
    MERGE (d)-[:HAS_PROPERTY]->(p);`;

    if (!existsSync("cypher/")) mkdirSync("cypher/");
    writeFileSync(`cypher/${Path.parse(file).name}-seed.cypher`, diseaseAndHeadersUpdateQuery);

    console.log(chalk.green(chalk.bold("[LOG]"), `Properties updated: ${secondColumn.length}`));

    await session.run(diseaseAndHeadersUpdateQuery, {
      map: properties,
    });

    const end = new Date().getTime();
    console.log(chalk.green(chalk.bold("[LOG]"), "Added Disease, Headers to database (If not already present)"));
    console.log(chalk.green(chalk.bold("[LOG]"), `Time taken: ${(end - start) / 1000} seconds`));
    console.log(chalk.green(chalk.bold("[LOG]"), "Data seeding completed"));
  } catch (error) {
    console.error(chalk.bold("[ERROR]"), error);
    process.exit(1);
  } finally {
    await session.close();
    await driver.close();
  }
})();
