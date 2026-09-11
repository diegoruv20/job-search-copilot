const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");

function virtualenvPython(root = ROOT) {
  const candidates = [
    path.join(root, ".venv", "Scripts", "python.exe"),
    path.join(root, ".venv", "bin", "python"),
  ];
  return candidates.find((candidate) => fs.existsSync(candidate));
}

function main(root = ROOT) {
  const python = virtualenvPython(root);
  if (!python) {
    console.error(
      "Job Search Copilot is not set up. Run `python scripts/bootstrap.py` " +
        "from the repository root.",
    );
    return 1;
  }

  const result = spawnSync(python, [path.join(root, "mcp_server.py")], {
    cwd: root,
    stdio: "inherit",
  });
  if (result.error) {
    console.error(`Unable to start Job Search Copilot MCP: ${result.error.message}`);
    return 1;
  }
  return result.status ?? 1;
}

if (require.main === module) {
  process.exitCode = main();
}

module.exports = { main, virtualenvPython };
