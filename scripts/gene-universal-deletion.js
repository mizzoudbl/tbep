import yargs from "yargs";
import chalk from "chalk";
import inquirer from "inquirer";
import neo4j from "neo4j-driver";

const defaultUsername = "neo4j";
const defaultDatabase = "tbep";
const defaultDbUrl = "bolt://localhost:7687";
const DISEASE_DEPENDENT_FIELDS = ["OpenTargets", "DEG"];
const DISEASE_INDEPENDENT_FIELDS = [
  "Pathway",
  "Druggability",
  "TE",
  "OT_Prioritization",
];

const args = yargs(process.argv.slice(2))
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
  .option("disease", {
    alias: "D",
    description: "Specify the disease name",
    type: "string",
  })
  .option("all", {
    description: "Delete all data of that type",
    type: "boolean",
  })
  .option("diseaseIndependent", {
    alias: "di",
    description: "Specify whether data is disease independent",
    type: "boolean",
  })
  .option("type", {
    alias: "t",
    description: "Specify the type of data to delete",
    type: "string",
  })
  .option("header", {
    alias: "H",
    description: "Headers to explicitly delete",
    type: "array",
  })
  .option("noHeader", {
    alias: "nh",
    description: "Disable headers",
    type: "boolean",
    default: false,
  })
  .help()
  .alias("help", "h")
  .version("1.0.0")
  .alias("version", "v")
  .usage(
    chalk.green(
      "Usage: $0 [-U | --dbUrl] <url> [-u | --username] <username> [-p | --password] <password> [-d | --database] <database> [-D | --disease] <disease> [-t | --type] <type> [-di | --diseaseIndependent]"
    )
  )
  .example(
    chalk.blue(
      "node $0 -U bolt://localhost:7687 -u neo4j -p password -d tbep -t TE --di --nh"
    )
  )
  .example(
    chalk.blue(
      "node $0 -U bolt://localhost:7687 -u neo4j -p password -d tbep -D ALS -t GWAS -H p-value,OR"
    )
  )
  .example(chalk.cyan("Load data in Neo4j")).argv;

async function promptForDetails(answer) {
  const questions = [
    !answer.dbUrl && {
      type: "input",
      name: "dbUrl",
      message: "Enter the database URL:",
      default: defaultDbUrl,
      required: true,
    },
    !answer.username && {
      type: "input",
      name: "username",
      message: "Enter the database username:",
      default: defaultUsername,
      required: true,
    },
    !answer.password && {
      type: "password",
      name: "password",
      mask: "*",
      message: "Enter the database password:",
      required: true,
    },
    !answer.database && {
      type: "input",
      name: "database",
      message: "Enter the database name:",
      default: defaultDatabase,
      required: true,
    },
    !(answer.disease || answer.all) && {
      type: "input",
      name: "disease",
      message:
        "Enter the disease ID(type all if data for all disease to be deleted) (Press Enter if disease independent):",
    },
    !answer.type &&
      !answer.diseaseIndependent && {
        type: "list",
        name: "type",
        message: "Enter the type of data to delete:",
        choices: DISEASE_DEPENDENT_FIELDS.concat(
          DISEASE_INDEPENDENT_FIELDS
        ).concat("Custom"),
        required: true,
      },
    !answer.header && {
      type: "input",
      name: "header",
      message: "Enter the headers to forcefully delete: (comma separated)",
      filter: (input) => input.split(",").map((header) => header.trim()),
    },
  ].filter(Boolean);

  return inquirer.prompt(questions);
}

(async () => {
  let {
    dbUrl,
    username,
    password,
    database,
    disease,
    diseaseIndependent,
    type,
    header,
    noHeader,
    all,
  } = await args;
  console.info(chalk.blue.bold("[INFO]"), chalk.cyan("GWAS -> OpenTargets"));
  console.info(
    chalk.blue.bold("[INFO]"),
    chalk.cyan("Genetics -> OpenTargets")
  );
  console.info(chalk.blue.bold("[INFO]"), chalk.cyan("LogFC -> DEG"));
  console.info(chalk.blue.bold("[INFO]"), chalk.cyan("GDA -> OpenTargets"));

  if (
    !dbUrl ||
    !username ||
    !password ||
    !database ||
    !(disease || all) ||
    !type ||
    !header
  ) {
    try {
      const answers = await promptForDetails({
        dbUrl,
        username,
        password,
        database,
        disease,
        all,
        type,
        ...(noHeader && { header: [] }),
        diseaseIndependent,
      });
      dbUrl ||= answers.dbUrl;
      username ||= answers.username;
      password ||= answers.password;
      database ||= answers.database;
      disease ||= answers.disease?.toUpperCase();
      type ||= answers.type;
      header ||= answers.header || [];
    } catch (error) {
      console.info(chalk.blue.bold("[INFO]"), chalk.cyan("Exiting..."));
      process.exit(0);
    }
  }
  if (header.length > 0 && header[0] !== "") {
    console.log(chalk.green(chalk.bold("[LOG]"), "Headers:"));
    console.log(header);
  }

  disease = DISEASE_INDEPENDENT_FIELDS.includes(type)
    ? undefined
    : all || disease === "all"
    ? "_"
    : disease?.toUpperCase();
  const driver = neo4j.driver(dbUrl, neo4j.auth.basic(username, password));
  const session = driver.session({ database: database });
  const column = `${disease ?? ""}${type}_`;
  try {
    const query = `
      MATCH (p:Property) WHERE p.name CONTAINS $column OR p.name IN $header
      WITH COLLECT(p.name) AS properties
      CALL apoc.periodic.iterate(
      'MATCH (g:Gene) RETURN g',
      'CALL apoc.create.removeProperties(g,$properties) YIELD node FINISH',
      { batchSize:1000, parallel:true, params: { properties: properties } })
      YIELD committedOperations
      RETURN properties, committedOperations;
      `;
    console.log(chalk.green(chalk.bold("[LOG]"), "This will take a while..."));
    const start = new Date().getTime();
    const result = await session.run(query, { header, column });
    const end = new Date().getTime();

    console.log(
      chalk.green(
        chalk.bold("[LOG]"),
        `Successfully deleted ${type} data for ${
          disease || "disease independent"
        } data`
      )
    );
    console.log(
      chalk.green(
        chalk.bold("[LOG]"),
        `Properties deleted: \n${result.records[0]
          .get("properties")
          .map((k) => `- ${k}`)
          .join("\n")}`
      )
    );
    console.log(
      chalk.green(
        chalk.bold("[LOG]"),
        `Committed operations: ${result.records[0].get("committedOperations")}`
      )
    );
    console.log(
      chalk.green(
        chalk.bold("[LOG]"),
        `Time taken: ${(end - start) / 1000} seconds`
      )
    );

    const deleteQuery =
      "MATCH (p:Property) WHERE p.name IN $header OR p.name CONTAINS $column DETACH DELETE p;";
    await session.run(deleteQuery, { header, column });
    await session.run(
      "MATCH (d:Disease&!Property) WHERE NOT (d)-[:HAS_PROPERTY]->() DELETE d;"
    );
    console.log(
      chalk.green(
        chalk.bold("[LOG]"),
        `Successfully updated ${disease || "disease independent"} data`
      )
    );
  } catch (error) {
    console.error(
      chalk.red(chalk.bold("[ERROR]"), `Error deleting ${type} data`),
      error
    );
  } finally {
    await session.close();
    await driver.close();
  }
})();
