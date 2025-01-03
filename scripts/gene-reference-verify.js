import yargs from "yargs";
import inquirer from "inquirer";
import chalk from "chalk";
import csv from "csv-parser";
import { createReadStream, createWriteStream, existsSync } from "node:fs";
import { createInterface } from "node:readline";
import Path from "node:path";

const FILETYPE = ["universal", "network"];
const defaultPrimaryHeader = "Ensembl gene ID";
const defaultSecondaryHeader = "Ensembl ID(supplied by Ensembl)";

const argv = yargs(process.argv.slice(2))
	.option("reference-genome", {
		alias: "ref",
		description: "CSV file containing reference genome",
		type: "string",
	})
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
	.option("primary-header", {
		description: "Primary column in reference genome",
		type: "string",
	})
	.option("secondary-header", {
		description: "Secondary column in reference genome",
		type: "string",
	})
	.option("type", {
		alias: "t",
		description: "Verification for which type of file",
		type: "string",
		choices: FILETYPE,
	})
	.help()
	.alias("help", "h")
	.version("1.0.0")
	.usage(
		chalk.green(
			"Usage: $0 [--ref | --reference-genome] <filename> [-i | --input-file] <filename> [-o | --output-file] <filename> [-t | --type] <universal | network>"
		)
	)
	.example(
		chalk.blue(
			"node $0 -ref genome.csv -i input.csv -o output.csv -t universal"
		)
	)
	.example(chalk.cyan("Verify universal data against reference genome")).argv;

async function promptForDetails(answer) {
	const questions = [
		!answer.referenceGenome && {
			type: "input",
			name: "referenceGenome",
			message: "Enter reference genome file path:",
			validate: (input) => {
				input = input.trim();
				if (Path.extname(input) !== ".csv") return "Please enter a CSV file";
				if (!existsSync(input))
					return "File does not exist in this directory. Please enter a valid file path";
				return true;
			},
		},
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
		!answer.type && {
			type: "list",
			name: "type",
			message: "Enter type for verification for which type of file",
			choices: FILETYPE,
			required: true,
		},
		!answer.primaryHeader &&
		(!answer.type || answer.type === "universal") && {
			type: "input",
			name: "primaryHeader",
			message: "Enter primary column in reference genom",
			default: defaultPrimaryHeader,
			required: false,
		},
		!answer.secondaryHeader &&
		(!answer.type || answer.type === "universal") && {
			type: "input",
			name: "secondaryHeader",
			message: "Enter secondary column in reference genom",
			default: defaultSecondaryHeader,
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
	let {
		inputFile,
		outputFile,
		referenceGenome,
		primaryHeader,
		secondaryHeader,
		type,
	} = await argv;

	try {
		if (
			!inputFile ||
			!referenceGenome ||
			!primaryHeader ||
			!secondaryHeader ||
			!type
		) {
			const answers = await promptForDetails({
				inputFile,
				referenceGenome,
				outputFile,
				primaryHeader,
				secondaryHeader,
				type,
			});
			inputFile ||= answers.inputFile;
			outputFile ||=
				answers.outputFile ||
				`${inputFile.split(".").slice(0, -1)}-verified.csv`;
			referenceGenome ||= answers.referenceGenome;
			primaryHeader ||= answers.primaryHeader;
			secondaryHeader ||= answers.secondaryHeader;
			type ||= answers.type;
		}
	} catch (error) {
		console.info(chalk.blue.bold("[INFO]"), chalk.cyan("Exiting..."));
		process.exit(0);
	}
	fileValidation(referenceGenome);
	fileValidation(inputFile);
	fileValidation(outputFile, false);

	const geneIDsSet = new Set();
	const isUniversal = type === "universal";
	let lineCount = 0;
	let filteredRows = 0;

	await new Promise((resolve, reject) => {
		createReadStream(referenceGenome)
			.pipe(csv())
			.on("data", (data) => {
				geneIDsSet.add(data[primaryHeader] || data[secondaryHeader]);
			})
			.on("end", () => {
				geneIDsSet.delete("");
				console.log(
					chalk.green(
						chalk.bold("[LOG]"),
						`GeneID Set size: ${geneIDsSet.size}`
					)
				);
				resolve();
			})
			.on("error", (err) => {
				console.error(
					chalk.red("[ERROR]"),
					"Error reading reference genome:",
					err
				);
				process.exit(1);
			});
	});

	const outputFileWriter = createWriteStream(outputFile);
	createInterface({
		input: createReadStream(inputFile),
	})
		.on("line", (line) => {
			if (
				lineCount++ === 0 ||
				(isUniversal
					? geneIDsSet.has(
						line
							.split(",")
							.shift()
							.replace(/^['\s"]*|['\s"]*$/g, "")
					)
					: line
						.split(",")
						.slice(0, 2)
						.every((gene) => geneIDsSet.has(gene)))
			) {
				++filteredRows;
				outputFileWriter.write(`${line}\n`);
			}
		})
		.on("close", () => {
			console.log(
				chalk.green(chalk.bold("[LOG]"), "CSV verified successfully.")
			);
			console.log(
				chalk.green(chalk.bold("[LOG]"), `Total filtered rows: ${filteredRows}`)
			);
			console.log(
				chalk.green(chalk.bold("[LOG]"), `Output file: ${outputFile}`)
			);
		});
})();
