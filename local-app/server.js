const express = require('express');
const path = require('path');
const fs = require('fs').promises;
const cors = require('cors');

const app = express();
const PORT = 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Serve static files from data directory
app.use('/data', express.static(path.join(__dirname, '..', 'data')));

// Helper function to read JSON files
async function readJSONFile(filePath) {
  try {
    const data = await fs.readFile(filePath, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error(`Error reading ${filePath}:`, error.message);
    return null;
  }
}

// Helper function to read text files
async function readTextFile(filePath) {
  try {
    const data = await fs.readFile(filePath, 'utf8');
    return data;
  } catch (error) {
    console.error(`Error reading ${filePath}:`, error.message);
    return null;
  }
}

// API Routes

// Get all tags
app.get('/api/tags', async (req, res) => {
  try {
    const tagsPath = path.join(__dirname, '..', 'data', 'tags.json');
    const tags = await readJSONFile(tagsPath);
    if (tags) {
      res.json(tags);
    } else {
      res.status(404).json({ error: 'Tags not found' });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get detection data for a specific tag
app.get('/api/detections/:tagId', async (req, res) => {
  try {
    const tagId = req.params.tagId;
    const detectionsPath = path.join(__dirname, '..', 'data', 'evidence_detections', `${tagId}_detections.json`);
    const detections = await readJSONFile(detectionsPath);
    if (detections) {
      res.json(detections);
    } else {
      res.status(404).json({ error: 'Detections not found' });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get summary for a specific tag
app.get('/api/summary/:tagId', async (req, res) => {
  try {
    const tagId = req.params.tagId;
    const summaryPath = path.join(__dirname, '..', 'data', 'evidence_detections', `${tagId}_summary.txt`);
    const summary = await readTextFile(summaryPath);
    if (summary !== null) {
      res.json({ summary });
    } else {
      res.status(404).json({ error: 'Summary not found' });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get all detections
app.get('/api/detections', async (req, res) => {
  try {
    const detectionsDir = path.join(__dirname, '..', 'data', 'evidence_detections');
    const files = await fs.readdir(detectionsDir);
    const detectionFiles = files.filter(f => f.endsWith('_detections.json'));
    
    const allDetections = [];
    for (const file of detectionFiles) {
      const filePath = path.join(detectionsDir, file);
      const detection = await readJSONFile(filePath);
      if (detection) {
        allDetections.push(detection);
      }
    }
    
    res.json(allDetections);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get all available data (tags + detections combined)
app.get('/api/all-data', async (req, res) => {
  try {
    const tagsPath = path.join(__dirname, '..', 'data', 'tags.json');
    const tags = await readJSONFile(tagsPath) || [];
    
    const detectionsDir = path.join(__dirname, '..', 'data', 'evidence_detections');
    const files = await fs.readdir(detectionsDir);
    const detectionFiles = files.filter(f => f.endsWith('_detections.json'));
    
    const detectionsMap = {};
    for (const file of detectionFiles) {
      const filePath = path.join(detectionsDir, file);
      const detection = await readJSONFile(filePath);
      if (detection) {
        detectionsMap[detection.tag_id] = detection;
      }
    }
    
    // Combine tags with their detections
    const combinedData = tags.map(tag => ({
      ...tag,
      detection: detectionsMap[tag.id] || null
    }));
    
    res.json(combinedData);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Serve main page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Server running at http://localhost:${PORT}`);
  console.log(`📊 View your data at http://localhost:${PORT}`);
});

