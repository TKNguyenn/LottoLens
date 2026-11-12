// Development-only extraction from the approved, self-contained HTML.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const html = fs.readFileSync(path.join(__dirname, 'lottolens-onboarding.html'), 'utf8');
const captures = JSON.parse(html.match(/<script id="captures" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const copy = vm.runInNewContext('(' + html.match(/const copy = ([\s\S]*?);\s*const storage/)[1] + ')');
const folder = path.join(__dirname, 'assets');
fs.mkdirSync(folder, { recursive: true });
const shots = {};
for (const [key, [base64, width, height, marks]] of Object.entries(captures)) {
  if (key.endsWith('-home')) continue;
  fs.writeFileSync(path.join(folder, key + '.webp'), Buffer.from(base64, 'base64'));
  shots[key] = { width, height, marks };
}
fs.writeFileSync(path.join(folder, 'guide.json'), JSON.stringify({ copy, shots }, null, 2) + '\n');
console.log('Extracted', Object.keys(shots).length, 'lossless tutorial images and bilingual copy.');
