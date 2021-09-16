const { env } = require("process");
const { replaceInFile } = require("replace-in-file");

const config = {
  files: ["robotcode/_version.py", "pyproject.toml"],
  from: /(^_*version_*\s*=\s*['"])([^'"]*)(['"])/gm,
  to: "$1" + env.npm_package_version + "$3",
};
replaceInFile(config, function (error, results) {
  if (error) {
    console.error(error);
  }
  if (results) {
    for (const result of results) {
      console.log(`${result.file} has ${result.hasChanged ? "" : "not "}changed`);
    }
  }
});
