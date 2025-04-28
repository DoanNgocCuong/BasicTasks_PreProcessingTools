  // Lấy systemPrompt và userInputPrompt từ các sheet tương ứng
var userInputPrompt = getDataFromSheet(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.TRANSCRIPTION);

function runDetectWarmLeadWrap() {
  var systemPrompt = getDataFromSheet(CONFIG.SHEETS.SYSTEM_PROMPT, CONFIG.SHEETS_RANGES.SYSTEM_PROMPT.DETECT_WARM_LEAD_WRAP_SYSTEM_PROMPT);
  var openAIResponse = getOpenAIResponse(systemPrompt, userInputPrompt, CONFIG.API_KEY);
  writeResponseToSheet(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.DETECTED_JSON.DETECT_WARM_LEAD_WRAP_SECTION, openAIResponse);
}
