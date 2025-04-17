import neo4j from "neo4j-driver";
import inquirer from "inquirer";
import chalk from "chalk";
import yargs from "yargs";
import Path from "node:path";

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
  ].filter(Boolean);

  return inquirer.prompt(questions);
}

(async () => {
  let { file, dbUrl, username, password, database } = await argv;
  console.warn(
    chalk.bold("[WARN]"),
    "Make sure to not enter header names in CSV file"
  );
  console.info(
    chalk.blue.bold("[INFO]"),
    chalk.cyan("'property name,property description' should be the format of CSV file")
  );
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

  const driver = neo4j.driver(dbUrl, neo4j.auth.basic(username, password));
  const session = driver.session({ database });

  try {
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
			MATCH (p:Property { name: line[0]})
			SET p.description = line[1]
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
        `Nodes Created: ${result.summary.counters.updates().nodesCreated}`
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
      "Check if file path is correct and file is accessible"
    );
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
