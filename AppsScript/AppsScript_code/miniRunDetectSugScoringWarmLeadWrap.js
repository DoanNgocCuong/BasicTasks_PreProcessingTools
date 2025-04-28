// function runDetectSugScoringWarmLeadWrap() {
//   runDetectWarmLeadWram();
//   runExtendWarmLeadWrap();
//   runSugScoreWarmLeadWrap();
//   copyDataBetweenSheets('used', 'B2', 'Output mẫu', 'E3');
//   copyDataBetweenSheets('used', 'D2', 'Output mẫu', 'F3');
//   copyDataBetweenSheets('used', 'D3', 'Output mẫu', 'F4');
//   copyDataBetweenSheets('used', 'D4', 'Output mẫu', 'F5');
  
// }




function runDetectSugScoringWarmLeadWrap() {
  runDetectWarmLeadWram();
  runExtendWarmLeadWrap();
  runSugScoringWarmLeadWrap();
  
  // Copy detected JSON data
  copyDataBetweenSheets(
    CONFIG.SHEETS.BACKEND, 
    CONFIG.SHEETS_RANGES.BACKEND.DETECTED_JSON.DETECT_WARM_LEAD_WRAP_SECTION, 
    CONFIG.SHEETS.OUTPUT, 
    CONFIG.SHEETS_RANGES.OUTPUT.DETECTED_JSON.DETECT_WARM_LEAD_WRAP_SECTION
  );
  
  // Copy suggested scoring data
  copyDataBetweenSheets(
    CONFIG.SHEETS.BACKEND, 
    CONFIG.SHEETS_RANGES.BACKEND.SUG_SCORING.WARM_UP, 
    CONFIG.SHEETS.OUTPUT, 
    CONFIG.SHEETS_RANGES.OUTPUT.SUG_SCORING.WARM_UP
  );
  copyDataBetweenSheets(
    CONFIG.SHEETS.BACKEND, 
    CONFIG.SHEETS_RANGES.BACKEND.SUG_SCORING.LEAD_IN, 
    CONFIG.SHEETS.OUTPUT, 
    CONFIG.SHEETS_RANGES.OUTPUT.SUG_SCORING.LEAD_IN
  );
  copyDataBetweenSheets(
    CONFIG.SHEETS.BACKEND, 
    CONFIG.SHEETS_RANGES.BACKEND.SUG_SCORING.WRAP_UP, 
    CONFIG.SHEETS.OUTPUT, 
    CONFIG.SHEETS_RANGES.OUTPUT.SUG_SCORING.WRAP_UP
  );
}