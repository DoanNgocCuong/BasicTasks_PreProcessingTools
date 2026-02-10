function testOpenAIResponse() {
  // Chuỗi systemPrompt và userInputPrompt để kiểm tra
  var systemPrompt = "You are a helpful assistant.";
  var userInputPrompt = "Tell me a joke.";

  // Đặt API key của bạn
  var apiKey = ''; // Thay bằng API key của bạn

  try {
    // Gửi yêu cầu tới OpenAI và nhận phản hồi
    var openAIResponse = getOpenAIResponse(systemPrompt, userInputPrompt, apiKey);
    
    // Ghi phản hồi vào một ô cụ thể trong Sheets
    writeResponseToSheet('Responses', 'B1', openAIResponse);
    
  } catch (error) {
    Logger.log('Lỗi: ' + error.message);
  }
}
