const { EOL } = require("os");
const { env } = require("process");
const { replaceInFile } = require("replace-in-file");

const versionFilesOption = {
  files: ["robotcode/_version.py", "pyproject.toml"],
  from: /(^_*version_*\s*=\s*['"])([^'"]*)(['"])/gm,
  to: `\$1${env.npm_package_version || ""}\$3`,
};
replaceInFile(versionFilesOption, function (error, _results) {
  if (error) {
    console.error(error);
  }
});

const changelogOptions = {
  files: ["CHANGELOG.md"],
  from: /^(\#*\s*)(\[Unreleased\])$/gm,
  to: `\$1\$2${EOL}${EOL}\$1 ${env.npm_package_version || ""}`,
};
replaceInFile(changelogOptions, function (error, _results) {
  if (error) {
    console.error(error);
  }
});
