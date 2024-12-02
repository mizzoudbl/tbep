import neo4j from "neo4j-driver";
import inquirer from "inquirer";
import { createReadStream, createWriteStream, existsSync } from "node:fs";
import { createInterface } from "node:readline";
import yargs from "yargs";
import chalk from "chalk";
import { platform } from "node:os";

const defaultUsername = "neo4j";
const defaultDatabase = "tbep";
const defaultDbUrl = "bolt://localhost:7687";
const GENERAL_SYMBOLS = ["hgnc_gene_id", "Description", "Gene_name", "Gene name"];
const DISEASE_DEPENDENT_FIELDS = ['GWAS', 'GDA', 'LogFC', 'Genetics', 'DEG'];
const DISEASE_INDEPENDENT_FIELDS = ['Pathway', 'Druggability', 'TE', 'Database'];
const RENAMED_FIELDS = {
  "GWAS": "Genetics",
  "LogFC": "DEG",
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
  .option("header", {
    alias: "H",
    description: "Headers to forcefully include",
    type: "array",
  })
  .option("no-header", {
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
      "Usage: $0 [-f | --file] <filename> [-U | --dbUrl] <url> [-u | --username] <username> [-p | --password] <password> [-d | --database] <database> [-D | --disease] <disease> [-H | --header] <headers>",
    )
  )
  .example(
    chalk.blue(
      "node $0 -f universal.csv -U bolt://localhost:7687 -u neo4j -p password -d tbep -D ALS --no-header"
    ),
    chalk.cyan("Load data in Neo4j"),
  ).argv;

async function promptForDetails(answer) {
  const questions = [
    !answer.file && {
      type: "input",
      name: "file",
      message: "Enter the file path:",
      validate: (input) => {
        input = input?.trim();
        if (!input.endsWith(".csv")) {
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
    !answer.disease && {
      type: "input",
      name: "disease",
      message: "Enter the disease name: (Press Enter if disease independent data)",
    },
    !answer.header && {
      type: "input",
      name: "header",
      message: "Enter the headers to forcefully include: (comma separated)",
      filter: (input) => input.split(",").map((header) => header.trim()),
    }
  ].filter(Boolean);

  const answers = await inquirer.prompt(questions);
  return {
    ...answer,
    ...answers,
  };
}

(async () => {
  let { file, dbUrl, username, password, database, disease, header, "no-header": noHeader } = await argv;

  if (!file || !dbUrl || !username || !password || !database || !disease || !header) {
    try {
      const answers = await promptForDetails({
        file,
        dbUrl,
        username,
        password,
        database,
        disease,
        ...(noHeader && { header: [] }),
      });
      file = answers.file;
      dbUrl = answers.dbUrl;
      username = answers.username;
      password = answers.password;
      database = answers.database;
      disease = answers.disease.toUpperCase();
      header = answers.header;
    } catch (error) {
      console.info(chalk.blue.bold("[INFO]"), chalk.cyan("Exiting..."));
      process.exit(0);
    }
  }
  if (platform() === "win32" && !/^https?:\/\//.test(file)) file = file.replace("/", "\\");
  if (!file.endsWith(".csv")) {
    console.error(chalk.bold("[ERROR]"), "File should be a CSV file. Exiting...");
    process.exit(1);
  }
  if (!existsSync(file)) {
    console.error(chalk.bold("[ERROR]"), "File does not exist in this directory. Exiting...");
    process.exit(1);
  }

  GENERAL_SYMBOLS.push(...header);
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
    const ID = initialHeaders.shift();
    const headers = initialHeaders
      .map((header) => {
        header = header.trim().replace(/"/g, "");

        for (const field of GENERAL_SYMBOLS) {
          if (new RegExp(`^${field}$`, "i").test(header)) {
            const res = RENAMED_FIELDS[field] ?? field;
            finalToInitialHeaders[res] = header;
            return res;
          }
        }

        // Conditions for modifying the header based on prefixes (ignoring case)
        if (disease) {
          const drHeader = header.replace(new RegExp(`^${disease}_`, "i"), "");
          for (const field of DISEASE_DEPENDENT_FIELDS) {
            if (new RegExp(`^${field}_`, "i").test(drHeader)) {
              const res = `${disease}_${RENAMED_FIELDS[field] ?? field}_${drHeader.slice(field.length + 1)}`;
              finalToInitialHeaders[res] = header;
              return res;
            }
          }
        }
        for (const field of DISEASE_INDEPENDENT_FIELDS) {
          if (new RegExp(`^${field}_`, "i").test(header)) {
            const res = `${RENAMED_FIELDS[field] ?? field}_${header.slice(field.length + 1)}`;
            finalToInitialHeaders[res] = header;
            return res;
          }
        }
        // Warn that the header is ignored if it doesn't meet the above criteria
        console.warn(chalk.bold("[WARN]"), `Header "${header}" Ignored`);
      })
      .filter(Boolean); // Filters out undefined or null values (i.e., ignored headers)

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
    LOAD CSV WITH HEADERS FROM '${/^https?:\/\//.test(file) ? file : `file:///${file}`}' AS row
    CALL {
      WITH row
      MATCH (g:Gene { ID: row.\`${ID}\` })
      SET ${headers.map((header) => `g.\`${header}\` = row.\`${finalToInitialHeaders[header]}\``).join(",\n")}   
    } IN 24 CONCURRENT TRANSACTIONS OF 1000 ROWS;
    `.replace(/"/g, "");

    const writeStream = createWriteStream(`${file}-seed.cypher`);
    writeStream.write(query);
    writeStream.end();

    try {
      console.log(chalk.green(chalk.bold("[LOG]"), "This will take a while..."));
      const start = new Date().getTime();
      const result = await session.run(query);
      const end = new Date().getTime();

      console.log(chalk.green(chalk.bold("[LOG]"), `Properties updated: ${result.summary.updateStatistics.updates().propertiesSet}`));
      console.log(chalk.green(chalk.bold("[LOG]"), `Time taken: ${(end - start) / 1000} seconds`));
      const indexQuery = "CREATE INDEX Gene_name IF NOT EXISTS FOR (g:Gene) ON (g.Gene_name)";
      await session.run(indexQuery);

      const diseaseAndHeadersUpdateQuery = `
      MERGE (s:Stats { version: 1 }) SET ${disease ? 's.disease = CASE WHEN NOT $disease IN COALESCE(s.disease,[]) THEN COALESCE(s.disease,[]) + $disease ELSE s.disease END,' : ''}
      s.common = apoc.coll.toSet(COALESCE(s.common, []) + ${disease ? '[h IN $headers WHERE NOT h STARTS WITH $disease + "_" ]' : '$headers'})
      ${disease ? `, s.${disease} = apoc.coll.toSet(COALESCE(s.${disease}, []) + [h IN $headers WHERE h STARTS WITH $disease + "_" ])` : ''};`;
      
      await session.run(diseaseAndHeadersUpdateQuery, { ...(disease && { disease }), headers });
      console.log(chalk.green(chalk.bold("[LOG]"), "Added Disease, Headers to Stats (If not already present)"));

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
