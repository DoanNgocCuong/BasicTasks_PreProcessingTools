var systemSheet = CONFIG.SHEETS.SYSTEM_PROMPT;
var userSheet = CONFIG.SHEETS.BACKEND;

function runSugScoringWarmLeadWrap() {
  runSugScoringWarmUp();
  runSugScoringLeadIn();
  runSugScoringWrapUp();
}

function runSugScoringWarmUp() {
  var systemPrompt = getDataFromSheet(systemSheet, CONFIG.SHEETS_RANGES.SYSTEM_PROMPT.SUG_SCORING_WARM_UP_SYSTEM_PROMPT);
  var userInputPrompt = getDataFromSheet(userSheet, CONFIG.SHEETS_RANGES.BACKEND.EXTENDED_TRANSCRIPTION.WARM_UP);
  var openAIResponse = getOpenAIResponse(systemPrompt, userInputPrompt, CONFIG.API_KEY);
  writeResponseToSheet(userSheet, CONFIG.SHEETS_RANGES.BACKEND.SUG_SCORING.WARM_UP, openAIResponse);
}

function runSugScoringLeadIn() {
  var systemPrompt = getDataFromSheet(systemSheet, CONFIG.SHEETS_RANGES.SYSTEM_PROMPT.SUG_SCORING_LEAD_IN_SYSTEM_PROMPT);
  var userInputPrompt = getDataFromSheet(userSheet, CONFIG.SHEETS_RANGES.BACKEND.EXTENDED_TRANSCRIPTION.LEAD_IN);
  var openAIResponse = getOpenAIResponse(systemPrompt, userInputPrompt, CONFIG.API_KEY);
  writeResponseToSheet(userSheet, CONFIG.SHEETS_RANGES.BACKEND.SUG_SCORING.LEAD_IN, openAIResponse);
}

function runSugScoringWrapUp() {
  var systemPrompt = getDataFromSheet(systemSheet, CONFIG.SHEETS_RANGES.SYSTEM_PROMPT.SUG_SCORING_WRAP_UP_SYSTEM_PROMPT);
  var userInputPrompt = getDataFromSheet(userSheet, CONFIG.SHEETS_RANGES.BACKEND.EXTENDED_TRANSCRIPTION.WRAP_UP);
  var openAIResponse = getOpenAIResponse(systemPrompt, userInputPrompt, CONFIG.API_KEY);
  writeResponseToSheet(userSheet, CONFIG.SHEETS_RANGES.BACKEND.SUG_SCORING.WRAP_UP, openAIResponse);
}

