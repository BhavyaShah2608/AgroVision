const fs = require('fs');
const path = require('path');

// Try to load .env file locally if it exists (for local testing/builds)
try {
  const envPath = path.join(__dirname, '.env');
  if (fs.existsSync(envPath)) {
    const envConfig = fs.readFileSync(envPath, 'utf8');
    envConfig.split('\n').forEach(line => {
      const trimmedLine = line.trim();
      if (!trimmedLine || trimmedLine.startsWith('#')) return;
      const index = trimmedLine.indexOf('=');
      if (index !== -1) {
        const key = trimmedLine.substring(0, index).trim();
        const val = trimmedLine.substring(index + 1).trim();
        process.env[key] = val;
      }
    });
  }
} catch (e) {
  console.log('No local .env file found or failed to parse. Using environment variables.');
}

const configPath = path.join(__dirname, 'Frontend', 'js', 'firebase-config.js');
let configContent = fs.readFileSync(configPath, 'utf8');

// Replace placeholders with environment variables
const replacements = {
  'REPLACE_API_KEY': process.env.FIREBASE_API_KEY,
  'REPLACE_AUTH_DOMAIN': process.env.FIREBASE_AUTH_DOMAIN,
  'REPLACE_PROJECT_ID': process.env.FIREBASE_PROJECT_ID,
  'REPLACE_STORAGE_BUCKET': process.env.FIREBASE_STORAGE_BUCKET,
  'REPLACE_MESSAGING_SENDER_ID': process.env.FIREBASE_MESSAGING_SENDER_ID,
  'REPLACE_APP_ID': process.env.FIREBASE_APP_ID
};

let missingKeys = [];
Object.keys(replacements).forEach(placeholder => {
  const envValue = replacements[placeholder];
  if (!envValue) {
    missingKeys.push(placeholder);
  } else {
    // Perform global replacement if needed (replace all occurrences of this placeholder)
    configContent = configContent.split(placeholder).join(envValue);
  }
});

if (missingKeys.length > 0) {
  console.error('WARNING: The following environment variables are missing during build:', missingKeys);
} else {
  console.log('Firebase configuration successfully injected into frontend assets!');
}

fs.writeFileSync(configPath, configContent, 'utf8');
