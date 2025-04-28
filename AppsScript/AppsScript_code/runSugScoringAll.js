var systemSheet = CONFIG.SHEETS.SYSTEM_PROMPT;
var userSheet = CONFIG.SHEETS.BACKEND;

function runSugScoring(systemPromptKey, userInputKey, outputKey) {
  var systemPrompt = getDataFromSheet(systemSheet, CONFIG.SHEETS_RANGES.SYSTEM_PROMPT[systemPromptKey]);
  var userInputPrompt = getDataFromSheet(userSheet, CONFIG.SHEETS_RANGES.BACKEND.EXTENDED_TRANSCRIPTION[userInputKey]);
  var openAIResponse = getOpenAIResponse(systemPrompt, userInputPrompt, CONFIG.API_KEY);
  writeResponseToSheet(userSheet, CONFIG.SHEETS_RANGES.BACKEND.SUG_SCORING[outputKey], openAIResponse);
}



function runSugScoringAll() {
  runSugScoringWarmLeadWrap();
  runSugScoringVocabPronunGrammarAll();
  runSugScoringICQsCCQsAll();
}

function runSugScoringWarmLeadWrap() {
  var sections = ['WARM_UP', 'LEAD_IN', 'WRAP_UP'];
  sections.forEach(function(section) {
    var systemPromptKey = 'SUG_SCORING_' + section + '_SYSTEM_PROMPT';
    runSugScoring(systemPromptKey, section, section);
  });
}


function runSugScoringVocabPronunGrammarAll() {
  var systemPromptKeys = {
    VOCAB: 'SUG_SCORING_VOCAB_SYSTEM_PROMPT',
    PRONUN: 'SUG_SCORING_PRONUN_SYSTEM_PROMPT',
    GRAMMAR: 'SUG_SCORING_GRAMMAR_SYSTEM_PROMPT'
  };

  for (var i = 1; i <= 6; i++) {
    var userInputKey = 'TEACHING_VOCAB_PRONUN_GRAMMAR_' + i;
    var outputKeys = {
      VOCAB: 'TEACHING_VOCAB_' + i,
      PRONUN: 'TEACHING_PRONUN_' + i,
      GRAMMAR: 'TEACHING_GRAMMAR_' + i
    };

    for (var key in systemPromptKeys) {
      runSugScoring(systemPromptKeys[key], userInputKey, outputKeys[key]);
    }
  }
}

function runSugScoringICQsCCQsAll() {
  var systemPromptKeys = {
    ICQS: 'SUG_SCORING_ICQS_SYSTEM_PROMPT',
    CCQs: 'SUG_SCORING_CCQS_SYSTEM_PROMPT'
  };

  for (var i = 1; i <= 5; i++) {
    var userInputKey = 'TEACHING_ICQS_CCQS_' + i;
    var outputKeys = {
      ICQS: 'TEACHING_ICQS_' + i,
      CCQs: 'TEACHING_CCQS_' + i
    };

    for (var key in systemPromptKeys) {
      runSugScoring(systemPromptKeys[key], userInputKey, outputKeys[key]);
    }
  }
}
