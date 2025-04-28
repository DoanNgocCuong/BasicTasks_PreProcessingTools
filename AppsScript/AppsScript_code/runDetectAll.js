  // Lấy systemPrompt và userInputPrompt từ các sheet tương ứng
var userInputPrompt = getDataFromSheet(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.TRANSCRIPTION);

function runDetectAll(){
  runDetectWarmLeadWrap();
  runDetectVocabPronunGrammar();
  runDetectICQsCCQs();
}

function runDetectWarmLeadWrap() {
  var systemPrompt = getDataFromSheet(CONFIG.SHEETS.SYSTEM_PROMPT, CONFIG.SHEETS_RANGES.SYSTEM_PROMPT.DETECT_WARM_LEAD_WRAP_SYSTEM_PROMPT);
    try {
      // Gửi yêu cầu tới OpenAI và nhận phản hồi
      var openAIResponse = getOpenAIResponse(systemPrompt, userInputPrompt, CONFIG.API_KEY);
      
      // Ghi phản hồi vào sheet
      // Kiểm tra sheet
      if (CONFIG.SHEETS_RANGES.BACKEND.DETECTED_JSON.DETECT_WARM_LEAD_WRAP_SECTION) {
        writeResponseToSheet(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.DETECTED_JSON.DETECT_WARM_LEAD_WRAP_SECTION, openAIResponse);
      } else {
        Logger.log('Error: DETECTED_JSON.DETECT_WARM_LEAD_WRAP_SECTION range is not defined in CONFIG');
      }
      
    } catch (error) {
      Logger.log('Error: ' + error.message);
    }
  }
  
  
function runDetectVocabPronunGrammar() {
  var systemPrompt = getDataFromSheet(CONFIG.SHEETS.SYSTEM_PROMPT, CONFIG.SHEETS_RANGES.SYSTEM_PROMPT.DETECT_VOCAB_PRONUN_GRAMMAR_SYSTEM_PROMPT);
  var openAIResponse = getOpenAIResponse(systemPrompt, userInputPrompt, CONFIG.API_KEY);
  writeResponseToSheet(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.DETECTED_JSON.DETECT_VOCAB_PRONUN_GRAMMAR_SECTION, openAIResponse);
}

function runDetectICQsCCQs() {
  var systemPrompt = getDataFromSheet(CONFIG.SHEETS.SYSTEM_PROMPT, CONFIG.SHEETS_RANGES.SYSTEM_PROMPT.DETECT_ICQS_CCQS_SYSTEM_PROMPT);
  var openAIResponse = getOpenAIResponse(systemPrompt, userInputPrompt, CONFIG.API_KEY);
  writeResponseToSheet(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.DETECTED_JSON.DETECT_ICQS_CCQS_SECTION, openAIResponse);
}