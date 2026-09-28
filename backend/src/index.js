require('dotenv').config();
const express = require('express');
const cors = require('cors');
const healthRoute = require('../routes/health');
const goldenRoute = require('../routes/golden');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

app.use('/api/health', healthRoute);
app.use('/api/golden', goldenRoute);

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
