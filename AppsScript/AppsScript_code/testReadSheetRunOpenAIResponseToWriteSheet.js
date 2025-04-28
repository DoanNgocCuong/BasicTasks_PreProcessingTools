// Hàm để đọc dữ liệu từ sheet và gửi yêu cầu tới OpenAI, sau đó ghi kết quả vào sheet khác
function testReadSheetRunOpenAIResponseToWriteSheet() {
    var systemPrompt = getDataFromSheet('Input', 'A1');
    var userInputPrompt = getDataFromSheet('Input', 'B1');
    var apiKey = ''; //
  
    try {
      var openAIResponse = getOpenAIResponse(systemPrompt, userInputPrompt, apiKey);
      writeResponseToSheet('Output', 'A1', openAIResponse);
      Logger.log('Response written to Output sheet');
    } catch (error) {
      Logger.log('Error: ' + error.message);
    }
  }