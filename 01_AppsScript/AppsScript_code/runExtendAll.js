var transcriptionStr = getDataFromSheet(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.TRANSCRIPTION);

function runExtendAll() {
  runExtendWarmLeadWrap();
  runExtendVocabPronunGrammar();
  runExtendICQsCCQs();
}

function runExtendWarmLeadWrap() {
  // Lấy dữ liệu từ các sheet tương ứng
  var sectionsStr = getDataFromSheet(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.DETECTED_JSON.DETECT_WARM_LEAD_WRAP_SECTION);
  
  var sections = parseSections(sectionsStr);
  if (sections === null) return;
  
  const keys = ["warm_up", "lead_in", "wrap_up"];
  
  keys.forEach(key => {
    // Gọi hàm extendTranscriptionSegment với các tham số đã chuyển đổi
    const extendedTranscription = extendTranscriptionSegment(
      transcriptionStr, 
      sections, 
      key, 
      CONFIG.DEFAULT_EXTENSION_TIME
    );
    
    // Ghi kết quả vào ô tương ứng trên sheet 'backend'
    const outputCell = CONFIG.SHEETS_RANGES.BACKEND.EXTENDED_TRANSCRIPTION[key.toUpperCase()];
    writeResponseToSheet(CONFIG.SHEETS.BACKEND, outputCell, extendedTranscription);
  });
}


function runExtendVocabPronunGrammar() {
  var sectionsStr = getDataFromSheet(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.DETECTED_JSON.DETECT_VOCAB_PRONUN_GRAMMAR_SECTION);
  var sections = parseSections(sectionsStr);
  const keys = ["teaching_vocab_pronun_grammar_1", "teaching_vocab_pronun_grammar_2", "teaching_vocab_pronun_grammar_3", "teaching_vocab_pronun_grammar_4", "teaching_vocab_pronun_grammar_5"];
  keys.forEach(key => {
    try {
      // main function
      const extendedTranscription = extendTranscriptionSegment(transcriptionStr, sections, key, CONFIG.DEFAULT_EXTENSION_TIME);
      const outputCell = CONFIG.SHEETS_RANGES.BACKEND.EXTENDED_TRANSCRIPTION[key.toUpperCase()];
      writeResponseToSheet(CONFIG.SHEETS.BACKEND, outputCell, extendedTranscription);
     // end main function
    } catch (error) {
      if (!error.message.includes("không tồn tại trong đối tượng")) {
        throw error;
      }
      // Bỏ qua lỗi nếu phần không tồn tại trong đối tượng
    }
  });
}

function runExtendICQsCCQs() {
  var sectionsStr = getDataFromSheet(CONFIG.SHEETS.BACKEND, CONFIG.SHEETS_RANGES.BACKEND.DETECTED_JSON.DETECT_ICQS_CCQS_SECTION);
  var sections = parseSections(sectionsStr);
  const keys = ["teaching_icqs_ccqs_1", "teaching_icqs_ccqs_2", "teaching_icqs_ccqs_3", "teaching_icqs_ccqs_4", "teaching_icqs_ccqs_5"];
  keys.forEach(key => {
    try{
      // main function
      const extendedTranscription = extendTranscriptionSegment(transcriptionStr, sections, key, CONFIG.DEFAULT_EXTENSION_TIME);
      const outputCell = CONFIG.SHEETS_RANGES.BACKEND.EXTENDED_TRANSCRIPTION[key.toUpperCase()];
      writeResponseToSheet(CONFIG.SHEETS.BACKEND, outputCell, extendedTranscription);
      // end main function
    } catch (error) {
      if (!error.message.includes("không tồn tại trong đối tượng")) {
        throw error;
      }
      // Bỏ qua lỗi nếu phần không tồn tại trong đối tượng
    }
  });
}