#!/usr/bin/env node

const fs = require('fs').promises;
const path = require('path');

const targetDir = process.argv[2] ? path.resolve(process.argv[2]) : process.cwd();
const topFlagIndex = process.argv.findIndex((arg) => arg === '--top' || arg === '-n');
const parsedTop = topFlagIndex !== -1 ? parseInt(process.argv[topFlagIndex + 1], 10) : NaN;
const topCount = Number.isFinite(parsedTop) && parsedTop > 0 ? parsedTop : 10;

function formatSize(bytes) {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value >= 10 || value % 1 === 0 ? 0 : 1)}${units[unit]}`;
}

async function walk(dir, files) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isSymbolicLink()) {
      continue;
    }
    if (entry.isDirectory()) {
      await walk(fullPath, files);
    } else if (entry.isFile()) {
      const stats = await fs.stat(fullPath);
      files.push({ path: fullPath, size: stats.size });
    }
  }
  return files;
}

async function main() {
  const files = await walk(targetDir, []);
  files.sort((a, b) => b.size - a.size);
  const topFiles = files.slice(0, topCount);

  if (topFiles.length === 0) {
    console.log('No files found.');
    return;
  }

  console.log(`Top ${topFiles.length} largest files under ${targetDir}:`);
  for (const file of topFiles) {
    console.log(`${formatSize(file.size).padStart(8)}  ${file.path}`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
