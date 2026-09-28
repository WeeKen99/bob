const express = require('express');
const router = express.Router();

router.get('/', (req, res) => {
  res.json({ status: 'ok', message: 'bob-a-thon API is running' });
});

module.exports = router;
