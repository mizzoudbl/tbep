import { promises as fs } from "fs";
import { join } from "path";

const MAPPING = {
  // Precedence
  maxClinicalTrialPhase: "Target in clinic",

  // tractability
  isInMembrane: "Membrane protein",
  isSecreted: "Secreted protein",
  hasLigand: "Ligand binder",
  hasSmallMoleculeBinder: "Small molecule binder",
  hasPocket: "Predicted pockets",

  // doability
  mouseOrthologMaxIdentityPercentage: "Mouse ortholog identity",
  hasHighQualityChemicalProbes: "Chemical probes",

  // safety
  geneticConstraint: "Genetic constraint",
  mouseKOScore: "Mouse models",
  hasTEP: "Gene essentiality",
  hasSafetyEvent: "Known safety events",
  isCancerDriverGene: "Cancer driver gene",
  paralogMaxIdentityPercentage: "Paralogues",
  tissueSpecificity: "Tissue specificity",
  tissueDistribution: "Tissue distribution",
};

/**
 * Maps column names from a CSV file according to the MAPPING dictionary.
 * @param {string} csvFilePath - Path to the CSV file to process
 * @returns {Promise<string>} - A new CSV string with mapped column names
 */
const mapColumnNames = async (csvFilePath) => {
  try {
    // Read the CSV file
    const data = await fs.readFile(csvFilePath, "utf8");

    // Split into lines and get header row
    const lines = data.split("\n");
    const header = lines[0].split(",");

    // Map the column names based on MAPPING
    const mappedHeader = header.map((colName) => {
      const trimmedColName = colName.trim();
      return MAPPING[trimmedColName]
        ? `OT_Prioritization_${MAPPING[trimmedColName]}`
        : trimmedColName;
    });

    // Replace the header with the mapped header
    lines[0] = mappedHeader.join(",");

    // Join the lines back together
    const mappedCsv = lines.join("\n");
    // Write the mapped CSV to a new file
    await fs.writeFile(csvFilePath, mappedCsv);

    console.log(`Mapped CSV saved to: ${csvFilePath}`);
    return mappedCsv;
  } catch (error) {
    console.error("Error processing CSV file:", error);
    throw error;
  }
};

const args = process.argv.slice(2);
const defaultCsvFilePath = join(
  import.meta.dirname,
  "data",
  "opentargets_target_prioritization_score.csv"
);

const csvFilePath = args[0] || defaultCsvFilePath;

mapColumnNames(csvFilePath).catch((err) => {
  console.error("Failed to process CSV:", err);
  process.exit(1);
});
