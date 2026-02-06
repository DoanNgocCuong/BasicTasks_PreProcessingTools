/**
 * Hàm để gửi yêu cầu tới OpenAI API và trả về phản hồi
 * @param {string} systemPrompt - Nội dung system prompt.
 * @param {string} userInputPrompt - Nội dung user input prompt.
 * @param {string} apiKey - API key của bạn.
 * @returns {string} - Phản hồi từ mô hình OpenAI.
 */
function getOpenAIResponse(systemPrompt, userInputPrompt, apiKey) {
  if (!systemPrompt || !userInputPrompt) {
    throw new Error('System prompt và user input prompt không được rỗng.');
  }

  var url = 'https://api.openai.com/v1/chat/completions';

  var payload = {
    model: 'gpt-4o-mini', // Thay đổi thành 'gpt-3.5-turbo' nếu cần
    messages: [
      {role: 'system', content: systemPrompt},
      {role: 'user', content: userInputPrompt}
    ]
  };

  var options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'Authorization': 'Bearer ' + apiKey
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  try {
    var response = UrlFetchApp.fetch(url, options);
    var responseCode = response.getResponseCode();
    var responseBody = response.getContentText();

    if (responseCode !== 200) {
      Logger.log('Yêu cầu API thất bại với trạng thái ' + responseCode + ': ' + responseBody);
      throw new Error('Yêu cầu API thất bại với trạng thái ' + responseCode + ': ' + responseBody);
    }

    var json = JSON.parse(responseBody);
    var result = json.choices[0].message.content;

    Logger.log('Phản hồi từ OpenAI: ' + result);
    return result;

  } catch (error) {
    Logger.log('Lỗi trong quá trình gọi API: ' + error.toString());
    throw error;
  }
}
