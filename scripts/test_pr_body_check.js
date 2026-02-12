#!/usr/bin/env node
/**
 * Local test for PR body template check logic (mirrors .github/workflows/pr_template_check.yml).
 * Usage: node scripts/test_pr_body_check.js [path-to-pr-body.md]
 * Default: .pr_body.md
 */

const fs = require('fs');
const path = require('path');

const bodyPath = process.argv[2] || path.join(__dirname, '..', '.pr_body.md');
let body = fs.readFileSync(bodyPath, 'utf8');

// Normalize: strip BOM, collapse line endings to \n
body = body
  .replace(/^\uFEFF/, '')
  .replace(/\r\n/g, '\n')
  .replace(/\r/g, '\n');

const isDraft = false;

function escapeHeading(h) {
  return h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function hasHeading(h) {
  const escaped = escapeHeading(h.replace(/\\(.)/g, '$1'));
  const re = new RegExp(`^#{1,6}\\s+${escaped}\\s*$`, 'im');
  return re.test(body);
}

function sectionText(heading) {
  const escaped = escapeHeading(heading);
  // Lookahead: next heading (^#{1,6}) OR end of string (?![\s\S]) — not $ which matches every EOL in multiline
  const re = new RegExp(
    `(^#{1,6}\\s+${escaped}\\s*$)([\\s\\S]*?)(?=^#{1,6}\\s+|(?![\\s\\S]))`,
    'im'
  );
  const m = body.match(re);
  return m ? m[2].trim() : '';
}

const CHECKED_BOX = /\[x\]|\u2611|&#x2611;/i;
function countCheckedInSection(heading) {
  const t = sectionText(heading);
  if (!t) return 0;
  const lines = t.split('\n');
  return lines.filter((line) => /^\s*-\s*/.test(line) && CHECKED_BOX.test(line)).length;
}

const requiredHeadings = ['Summary', 'Verification', 'Risk Assessment', 'Checklist (Ruthless)'];
const missingHeadings = requiredHeadings.filter((h) => !hasHeading(h));
if (missingHeadings.length) {
  console.error('FAIL: Missing sections:', missingHeadings.join(', '));
  process.exit(1);
}

const problems = [];

const riskChecked = countCheckedInSection('Risk Level');
const perfChecked = countCheckedInSection('Perf Impact');
const breakingChecked = countCheckedInSection('Breaking Change?');
const schemaChecked = countCheckedInSection('Config / Schema Changes');

if (riskChecked < 1) problems.push('Risk Level: check one of Low / Medium / High.');
if (perfChecked < 1) problems.push('Perf Impact: check at least one option.');
if (breakingChecked < 1) problems.push('Breaking Change?: check Yes or No.');
if (schemaChecked < 1) problems.push('Config / Schema Changes: check None or Yes.');

const verification = sectionText('Verification');
const requiredGates = sectionText('Required Gates');
const hasCleanup = /\/cleanup/.test(verification) || /\/cleanup/.test(requiredGates);
const hasCoverage = /\/coverage/.test(verification) || /\/coverage/.test(requiredGates);
if (!hasCleanup) problems.push('Verification must mention /cleanup (quality + tests).');
if (!hasCoverage) problems.push('Verification must mention /coverage (coverage threshold).');
if (!isDraft) {
  const gatesText = requiredGates || verification;
  const hasCheckedLineWith = (text) =>
    gatesText.split('\n').some((line) => /^\s*-\s*/.test(line) && CHECKED_BOX.test(line) && line.includes(text));
  if (!hasCheckedLineWith('/cleanup')) problems.push('Non-draft PRs: check the /cleanup gate in Required Gates.');
  if (!hasCheckedLineWith('/coverage')) problems.push('Non-draft PRs: check the /coverage gate in Required Gates.');
}

const summaryRaw = sectionText('Summary').replace(/<!--[\s\S]*?-->/g, '').replace(/\s/g, '');
if (summaryRaw.length < 20) {
  problems.push('Summary: add 1–3 sentences (not just placeholders).');
}

const testsSection = sectionText('Tests Added / Updated');
const hasTestBullets = /^\s*-\s+.+/m.test(testsSection);
const hasNone = /\bnone\b/i.test(testsSection);
if (!hasTestBullets && !hasNone) {
  problems.push('Tests Added / Updated: list tests or write "None" explicitly.');
}

const failureModes = sectionText('Failure Modes Considered');
const hasFailureBullets = /^\s*-\s+.+/m.test(failureModes);
const hasNA = /\b(n\/a|n\.a\.|none)\b/i.test(failureModes);
if (!hasFailureBullets && !hasNA) {
  problems.push('Failure Modes Considered: add at least one bullet or write N/A.');
}

if (problems.length) {
  console.error('FAIL: PR body check failed:\n- ' + problems.join('\n- '));
  process.exit(1);
}

console.log('OK: PR body passes all template checks.');
process.exit(0);
