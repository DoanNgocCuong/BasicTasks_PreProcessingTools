function runAllBackendAndCopyToOutput() {
  runAllBackend();
  copyBackendToOutput();
}

function runAllBackend(){
  runDetectAll();
  runExtendAll();
  runSugScoringAll();

}

// Copy kết quả từ Backend sang Output
function copyBackendToOutput() {
  // Copy DETECTED_JSON
  copyRange(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.DETECTED_JSON.DETECT_WARM_LEAD_WRAP_SECTION, 
            CONFIG.SHEETS.OUTPUT, CONFIG.SHEETS_RANGES.OUTPUT.DETECTED_JSON.DETECT_WARM_LEAD_WRAP_SECTION);
  copyRange(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.DETECTED_JSON.DETECT_VOCAB_PRONUN_GRAMMAR_SECTION, 
            CONFIG.SHEETS.OUTPUT, CONFIG.SHEETS_RANGES.OUTPUT.DETECTED_JSON.DETECT_VOCAB_PRONUN_GRAMMAR_SECTION);
  copyRange(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.DETECTED_JSON.DETECT_ICQS_CCQS_SECTION, 
            CONFIG.SHEETS.OUTPUT, CONFIG.SHEETS_RANGES.OUTPUT.DETECTED_JSON.DETECT_ICQS_CCQS_SECTION);

  // Copy SUG_SCORING
  copyRange(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.SUG_SCORING.WARM_UP, 
            CONFIG.SHEETS.OUTPUT, CONFIG.SHEETS_RANGES.OUTPUT.SUG_SCORING.WARM_UP);
  copyRange(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.SUG_SCORING.LEAD_IN, 
            CONFIG.SHEETS.OUTPUT, CONFIG.SHEETS_RANGES.OUTPUT.SUG_SCORING.LEAD_IN);
  copyRange(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.SUG_SCORING.WRAP_UP, 
            CONFIG.SHEETS.OUTPUT, CONFIG.SHEETS_RANGES.OUTPUT.SUG_SCORING.WRAP_UP);

  for (let i = 1; i <= 6; i++) {
    copyRange(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.SUG_SCORING[`TEACHING_VOCAB_${i}`], 
              CONFIG.SHEETS.OUTPUT, CONFIG.SHEETS_RANGES.OUTPUT.SUG_SCORING[`TEACHING_VOCAB_${i}`]);
    copyRange(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.SUG_SCORING[`TEACHING_GRAMMAR_${i}`], 
              CONFIG.SHEETS.OUTPUT, CONFIG.SHEETS_RANGES.OUTPUT.SUG_SCORING[`TEACHING_GRAMMAR_${i}`]);
    copyRange(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.SUG_SCORING[`TEACHING_PRONUN_${i}`], 
              CONFIG.SHEETS.OUTPUT, CONFIG.SHEETS_RANGES.OUTPUT.SUG_SCORING[`TEACHING_PRONUN_${i}`]);
  }

  for (let i = 1; i <= 5; i++) {
    copyRange(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.SUG_SCORING[`TEACHING_ICQS_${i}`], 
              CONFIG.SHEETS.OUTPUT, CONFIG.SHEETS_RANGES.OUTPUT.SUG_SCORING[`TEACHING_ICQS_${i}`]);
    copyRange(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.SUG_SCORING[`TEACHING_CCQS_${i}`], 
              CONFIG.SHEETS.OUTPUT, CONFIG.SHEETS_RANGES.OUTPUT.SUG_SCORING[`TEACHING_CCQS_${i}`]);
  }
}

function copyRange(sourceSheetName, sourceRange, destSheetName, destRange) {
  var sourceSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(sourceSheetName);
  var destSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(destSheetName);
  
  var sourceValues = sourceSheet.getRange(sourceRange).getValues();
  destSheet.getRange(destRange).setValues(sourceValues);
}