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

// 1. Process Frontend/js/firebase-config.js
const configPath = path.join(__dirname, 'Frontend', 'js', 'firebase-config.js');
if (fs.existsSync(configPath)) {
  let configContent = fs.readFileSync(configPath, 'utf8');
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
      configContent = configContent.split(placeholder).join(envValue);
    }
  });

  if (missingKeys.length > 0) {
    console.error('WARNING: The following environment variables are missing for firebase-config.js:', missingKeys);
  } else {
    console.log('Firebase configuration successfully injected!');
  }
  fs.writeFileSync(configPath, configContent, 'utf8');
}

// 2. Process Frontend/bot.html
const botPath = path.join(__dirname, 'Frontend', 'bot.html');
if (fs.existsSync(botPath)) {
  let botContent = fs.readFileSync(botPath, 'utf8');
  const geminiKey = process.env.GEMINI_API_KEY;
  if (!geminiKey) {
    console.error('WARNING: GEMINI_API_KEY environment variable is missing for bot.html!');
  } else {
    botContent = botContent.split('REPLACE_GEMINI_API_KEY').join(geminiKey);
    console.log('Gemini API key successfully injected into bot.html!');
  }
  fs.writeFileSync(botPath, botContent, 'utf8');
}
