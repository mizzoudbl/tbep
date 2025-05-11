import neo4j from "neo4j-driver";
import inquirer from "inquirer";
import chalk from "chalk";
import yargs from "yargs";
import Path from "node:path";

const defaultUsername = "neo4j";
const defaultDatabase = "tbep";
const defaultDbUrl = "bolt://localhost:7687";
const ID_TYPE = ["ENSEMBL-ID", "HGNC-Symbol"];

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
  .option("interactionType", {
    alias: "i",
    description: "Specify the interaction type",
    type: "string",
  })
  .option("id-type", {
    alias: "t",
    description: "Specify the ID type",
    type: "string",
    choices: ID_TYPE,
  })
  .help()
  .alias("help", "h")
  .version("1.0.0")
  .alias("version", "v")
  .usage(
    chalk.green(
      "Usage: $0 [-f | --file] <filename> [-U | --dbUrl] <url> [-u | --username] <username> [-p | --password] <password> [-d | --database] <database> [-i | --interactionType] <interactionType> [-t | --id-type] <Ensembl-ID | HGNC-Symbol>"
    )
  )
  .example(
    chalk.blue(
      "node $0 -f data.csv -U bolt://localhost:7687 -u neo4j -p password -d tbep -i PPI -t Ensembl-ID"
    )
  )
  .example(chalk.cyan("Load data in Neo4j")).argv;

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
    !answer.interactionType && {
      type: "input",
      name: "interactionType",
      message: "Enter the interaction type [Make sure it's just one word]:",
      required: true,
    },
    !answer.idType && {
      type: "input",
      name: "idType",
      message: "Select the ID type:",
      choices: ID_TYPE,
      default: ID_TYPE[0],
    },
  ].filter(Boolean);

  return inquirer.prompt(questions);
}

(async () => {
  let { file, dbUrl, username, password, database, interactionType, idType } =
    await argv;
  console.warn(
    chalk.yellow(
      chalk.bold("[WARN]"),
      "Make sure to not enter header names in CSV file"
    )
  );
  console.info(
    chalk.blue.bold("[INFO]"),
    chalk.cyan(
      "'1st ENSG Gene ID,2nd ENSG Gene ID,Score' should be the format of CSV file"
    )
  );
  if (
    !file ||
    !dbUrl ||
    !username ||
    !password ||
    !database ||
    !interactionType ||
    !idType
  ) {
    try {
      const answers = await promptForDetails({
        file,
        dbUrl,
        username,
        password,
        database,
        interactionType,
        idType,
      });
      file ||= answers.file;
      dbUrl ||= answers.dbUrl;
      username ||= answers.username;
      password ||= answers.password;
      database ||= answers.database;
      interactionType ||= answers.interactionType;
      idType ||= answers.idType;
    } catch (error) {
      console.info(chalk.blue.bold("[INFO]"), chalk.cyan("Exiting..."));
      process.exit(0);
    }
  }
  if (Path.extname(file) !== ".csv") {
    console.error(chalk.bold("[ERROR]"), "Please enter a CSV file. Exiting...");
    process.exit(1);
  }

  const driver = neo4j.driver(dbUrl, neo4j.auth.basic(username, password));
  const session = driver.session({
    database: database,
  });

  try {
    console.log(chalk.green(chalk.bold("[LOG]"), "Loading data into Neo4j..."));
    console.log(
      chalk.green(
        chalk.bold("[LOG]"),
        "This process will take some time. Please wait..."
      )
    );

    const query = `
		LOAD CSV FROM '${
      /^https?:\/\//.test(file)
        ? file
        : `file:///${file.replace(/^\.[\\/]+/, "")}`
    }' AS line
		CALL {
			WITH line
			MATCH (g1:Gene {${
        idType === ID_TYPE[0] ? "ID" : "Gene_name"
      }: toUpper(line[0])})
			MATCH (g2:Gene {${
        idType === ID_TYPE[0] ? "ID" : "Gene_name"
      }: toUpper(line[1])})
			MERGE (g1)-[r:${interactionType}]->(g2)
			ON CREATE SET r.score = toFloat(line[2])
		} IN TRANSACTIONS;
		`;
    // record execution time
    const start = new Date().getTime();
    const result = await session.run(query);
    const end = new Date().getTime();

    console.log(chalk.green(chalk.bold("[LOG]"), "Data loaded using LOAD CSV"));
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
