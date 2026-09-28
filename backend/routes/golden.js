const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const csv = require('csv-parse/sync');

const GOLDEN_CSV  = path.join(__dirname, '../../use-case-1/data/output/golden_customers.csv');
const DUPES_CSV   = path.join(__dirname, '../../use-case-1/data/output/duplicate_log.csv');
const CB_CSV      = path.join(__dirname, '../../use-case-1/data/source/core_banking.csv');
const CC_CSV      = path.join(__dirname, '../../use-case-1/data/source/credit_card.csv');
const MG_CSV      = path.join(__dirname, '../../use-case-1/data/source/mortgage.csv');

function readCsv(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  return csv.parse(content, { columns: true, skip_empty_lines: true });
}

router.get('/', (req, res) => {
  const golden     = readCsv(GOLDEN_CSV);
  const duplicates = readCsv(DUPES_CSV);
  const cb         = readCsv(CB_CSV);
  const cc         = readCsv(CC_CSV);
  const mg         = readCsv(MG_CSV);

  res.json({
    summary: {
      core_banking_records:  cb.length,
      credit_card_records:   cc.length,
      mortgage_records:      mg.length,
      total_raw_records:     cb.length + cc.length + mg.length,
      golden_records:        golden.length,
      duplicates_merged:     duplicates.length,
    },
    golden_customers: golden,
    duplicate_log:    duplicates,
  });
});

module.exports = router;
