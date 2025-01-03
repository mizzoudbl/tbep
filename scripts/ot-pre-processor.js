import yargs from "yargs";
import inquirer from "inquirer";
import chalk from "chalk";
import { existsSync, createWriteStream, createReadStream } from "node:fs";
import Path from "node:path";
import Papa from "papaparse";

const argv = yargs(process.argv.slice(2))
  .option("input-file", {
    alias: "i",
    description: "Input file to verify",
    type: "string",
  })
  .option("output-file", {
    alias: "o",
    description: "Output name of verified file",
    type: "string",
  })
  .help()
  .alias("help", "h")
  .version("1.0.0")
  .usage(
    chalk.green(
      "Usage: $0 [-i | --input-file] <filename> [-o | --output-file] <filename>"
    )
  )
  .example(chalk.blue("node $0 -i input.csv -o output.csv"))
  .example(chalk.cyan("Verify universal data against reference genome")).argv;

async function promptForDetails(answer) {
  const questions = [
    !answer.inputFile && {
      type: "input",
      name: "inputFile",
      message: "Enter input file path:",
      validate: (input) => {
        input = input.trim();
        if (Path.extname(input) !== ".csv") return "Please enter a CSV file";
        if (!existsSync(input))
          return "File does not exist in this directory. Please enter a valid file path";
        return true;
      },
    },
    !answer.outputFile && {
      type: "input",
      name: "outputFile",
      message: "Enter output file path: (optional)",
      required: false,
    },
  ].filter(Boolean);

  return inquirer.prompt(questions);
}

function fileValidation(file, checkExistence = true) {
  if (Path.extname(file) !== ".csv") {
    console.error(
      chalk.bold("[ERROR]"),
      `${file}: File should be a CSV file. Exiting...`
    );
    process.exit(1);
  }
  if (checkExistence && !existsSync(file)) {
    console.error(
      chalk.bold("[ERROR]"),
      `${file}: File does not exist in this directory. Exiting...`
    );
    process.exit(1);
  }
}

(async () => {
  let { inputFile, outputFile } = await argv;

  try {
    if (!inputFile || !outputFile) {
      const answers = await promptForDetails({
        inputFile,
        outputFile,
      });
      inputFile ||= answers.inputFile;
      outputFile ||=
        answers.outputFile ||
        `${inputFile.split(".").slice(0, -1)}-verified.csv`;
    }
  } catch (error) {
    console.info(chalk.blue.bold("[INFO]"), chalk.cyan("Exiting..."));
    process.exit(0);
  }
  fileValidation(inputFile);
  fileValidation(outputFile, false);

  let processedRows = 0;
  const suffix = Path.parse(inputFile)
    .name.replace(/^transformed_association/, "")
    .replace(/^target_prioritization_score/, "");
  const startTime = new Date().getTime();

  const outputStream = createWriteStream(outputFile);
  outputStream.write("node_id,property,value\n");

  Papa.parse(createReadStream(inputFile), {
    header: true,
    step: (result) => {
      const row = result.data;
      const headers = result.meta.fields;
      const nodeIdColumn = headers[0];
      
      for (const header of headers.slice(1)) {
        if (!Number.isNaN(Number.parseFloat(row[header]))) {
          const csvLine = `${row[nodeIdColumn]},${
            `${header}_OpenTargets${suffix}`
          },${row[header]}\n`;
          outputStream.write(csvLine);
          processedRows++;
        }
      }
    },
    complete: () => {
      outputStream.end();
      const endTime = new Date().getTime();
      console.log(
        chalk.green(
          chalk.bold("[SUCCESS]"),
          `Processed ${processedRows} rows in ${
            (endTime - startTime) / 1000
          } seconds`
        )
      );
    },
    error: (error) => {
      console.error(chalk.bold("[ERROR]"), error.message);
      process.exit(1);
    },
  });
})();
