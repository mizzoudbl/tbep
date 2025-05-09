import neo4j from "neo4j-driver";
import inquirer from "inquirer";
import {
  createReadStream,
  existsSync,
  writeFileSync,
  mkdirSync,
} from "node:fs";
import { createInterface } from "node:readline";
import yargs from "yargs";
import chalk from "chalk";
import Path from "node:path";

const defaultUsername = "neo4j";
const defaultDatabase = "tbep";
const defaultDbUrl = "bolt://localhost:7687";
const DISEASE_DEPENDENT_FIELDS = ["LogFC", "DEG", "OpenTargets"];
const DISEASE_INDEPENDENT_FIELDS = [
  "Druggability_Score",
  "Pathway",
  "Druggability",
  "TE",
  "OT_Prioritization",
];
const RENAMED_FIELDS = {
  Druggability_Score: "Druggability",
  LogFC: "DEG",
  "Gene name": "Gene_name",
};

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
  .option("disease", {
    alias: "D",
    description: "Specify the disease name",
    type: "string",
  })
  .option("diseaseIndependent", {
    alias: "di",
    description: "Specify whether data is disease independent",
    type: "boolean",
  })
  .option("header", {
    alias: "H",
    description: "Headers to forcefully include",
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
      "Usage: $0 [-f | --file] <filename> [-U | --dbUrl] <url> [-u | --username] <username> [-p | --password] <password> [-d | --database] <database> [-D | --disease] <disease> [-H | --header] <headers> [-di | --diseaseIndependent]"
    )
  )
  .example(
    chalk.blue(
      "node $0 -f universal.csv -U bolt://localhost:7687 -u neo4j -p password -d tbep -D ALS --nh"
    )
  )
  .example(
    chalk.blue(
      "node $0 -f universal.csv -U bolt://localhost:7687 -u neo4j -p password -d tbep --di --nh"
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
    !answer.disease &&
      !answer.diseaseIndependent && {
        type: "input",
        name: "disease",
        message:
          "Enter the disease name: (Press Enter if disease independent data)",
      },
    !answer.header && {
      type: "input",
      name: "header",
      message: "Enter the headers to forcefully include: (comma separated)",
      filter: (input) => input.split(",").map((header) => header.trim()),
    },
  ].filter(Boolean);

  return inquirer.prompt(questions);
}

(async () => {
  let {
    file,
    dbUrl,
    username,
    password,
    database,
    disease,
    header,
    noHeader,
    diseaseIndependent,
  } = await argv;
  if (
    !file ||
    !dbUrl ||
    !username ||
    !password ||
    !database ||
    !disease ||
    !header
  ) {
    try {
      const answers = await promptForDetails({
        file,
        dbUrl,
        username,
        password,
        database,
        disease,
        diseaseIndependent,
        ...(noHeader && { header: [] }),
      });
      file ||= answers.file;
      dbUrl ||= answers.dbUrl;
      username ||= answers.username;
      password ||= answers.password;
      database ||= answers.database;
      disease ||= answers.disease?.toUpperCase();
      header ||= answers.header || [];
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

  const finalToInitialHeaders = {};
  const readInterface = createInterface({
    input: createReadStream(file),
  });
  readInterface.once("line", async (line) => {
    readInterface.close();
    const initialHeaders = line.split(",");
    if (initialHeaders.length < 2) {
      console.error(
        chalk.bold("[ERROR]"),
        "CSV file must have at least two columns"
      );
      process.exit(1);
    }
    const ID = initialHeaders.shift()?.trim();
    const headers = initialHeaders
      .map((header) => {
        header = header.trim().replace(/^['\s"]*|['\s"]*$/g, "");

        // Conditions for modifying the header based on prefixes (ignoring case)
        if (disease) {
          const drHeader = header.replace(new RegExp(`^${disease}_`, "i"), "");
          for (const field of DISEASE_DEPENDENT_FIELDS) {
            if (new RegExp(`^${field}_`, "i").test(drHeader)) {
              const res = `${disease}_${
                RENAMED_FIELDS[field] ?? field
              }_${drHeader.slice(field.length + 1)}`;
              finalToInitialHeaders[res] = header;
              return res;
            }
          }
        }
        for (const field of DISEASE_INDEPENDENT_FIELDS) {
          if (new RegExp(`^${field}_`, "i").test(header)) {
            const res = `${RENAMED_FIELDS[field] ?? field}_${header.slice(
              field.length + 1
            )}`;
            finalToInitialHeaders[res] = header;
            return res;
          }
        }
        // Warn that the header is ignored if it doesn't meet the above criteria
        console.warn(chalk.bold("[WARN]"), `Header "${header}" Ignored`);
      })
      .filter(Boolean); // Filters out undefined or null values (i.e., ignored headers)

    if (headers.length === 0) {
      console.error(chalk.bold("[ERROR]"), "No headers to seed. Exiting...");
      process.exit(1);
    }
    console.log(
      chalk.green(
        chalk.bold("[LOG]"),
        "Headers (filtered):",
        chalk.underline(headers)
      )
    );
    console.log(
      chalk.green(chalk.bold("[LOG]"), "Gene ID Header:", chalk.underline(ID))
    );

    const driver = neo4j.driver(dbUrl, neo4j.auth.basic(username, password));
    const session = driver.session({
      database: database,
    });
    const query = `
    LOAD CSV WITH HEADERS FROM '${
      /^https?:\/\//.test(file)
        ? file
        : `file:///${Path.resolve(file)
            .split("scripts")
            .at(-1)
            .replace(/^\.[\\/]+/, "")
            .replace(/\\/g, "/")}`
    }' AS row
    CALL {
      WITH row
      MATCH (g:Gene { ID: row.\`${ID}\` })
      SET ${headers
        .map(
          (header) =>
            `g.\`${header}\` = row.\`${finalToInitialHeaders[header]}\``
        )
        .join(",\n")}   
    } IN 24 CONCURRENT TRANSACTIONS;
    `.replace(/"/g, "");

    if (!existsSync("cypher/")) mkdirSync("cypher/");
    writeFileSync(`cypher/${Path.parse(file).name}-seed.cypher`, query);

    try {
      console.log(
        chalk.green(chalk.bold("[LOG]"), "This will take a while...")
      );
      const start = new Date().getTime();
      const result = await session.run(query);
      const end = new Date().getTime();

      console.log(
        chalk.green(
          chalk.bold("[LOG]"),
          `Properties updated: ${
            result.summary.updateStatistics.updates().propertiesSet
          }`
        )
      );
      console.log(
        chalk.green(
          chalk.bold("[LOG]"),
          `Time taken: ${(end - start) / 1000} seconds`
        )
      );

      const { commonHeaders, diseaseHeaders } = headers.reduce(
        (acc, header) => {
          if (disease && header.startsWith(`${disease}_`)) {
            acc.diseaseHeaders.push(header);
          } else {
            acc.commonHeaders.push(header);
          }
          return acc;
        },
        { commonHeaders: [], diseaseHeaders: [] }
      );
      if (disease) {
        await session.run(
          `MERGE (d:Disease { ID: $disease }) WITH d
          UNWIND $diseaseHeaders AS diseaseHeader
          MERGE (dp:Property { name: diseaseHeader })
          MERGE (d)-[:HAS_PROPERTY]->(dp);`,
          { disease, diseaseHeaders }
        );
      }
      await session.run(
        `UNWIND $commonHeaders AS commonHeader
          MERGE (cp:Common&Property { name: commonHeader });`,
        { commonHeaders }
      );

      console.log(
        chalk.green(
          chalk.bold("[LOG]"),
          "Added Disease, Headers to database (If not already present)"
        )
      );

      console.log(chalk.green(chalk.bold("[LOG]"), "Data seeding completed"));
    } catch (error) {
      console.error(chalk.bold("[ERROR]"), error);
      process.exit(1);
    } finally {
      await session.close();
      await driver.close();
    }
  });
})();
