function runExtendWarmUp() {
  // Thông tin về transcription và sections
  var transcriptionInfo = { sheetName: 'backend', range: 'A2' };
  var sectionsInfo = { sheetName: 'backend', range: 'B2' };
  
  // Lấy dữ liệu từ các sheet tương ứng
  var transcriptionStr = getDataFromSheet(transcriptionInfo.sheetName, transcriptionInfo.range);
  var sectionsStr = getDataFromSheet(sectionsInfo.sheetName, sectionsInfo.range);
  
  // Parse sectionsStr to a JSON object
  var sections;
  try {
    sections = JSON.parse(sectionsStr);
    Logger.log('Parsed sections object: ' + JSON.stringify(sections));
  } catch (e) {
    Logger.log('Lỗi khi parsing JSON từ sections: ' + e.message);
    writeResponseToSheet('backend', 'D2', 'Lỗi: Không thể parse JSON từ dữ liệu sections');
    return;
  }
  
  const key = "warm_up"; // Thay đổi key này để lấy start và end của phần khác
  
  try {
    // Gọi hàm extendTranscriptionSegment với các tham số đã chuyển đổi
    const extendedTranscription = extendTranscriptionSegment(
      transcriptionStr, 
      sections, 
      key, 
      120 // extensionTime, mặc định là 120 giây
    );
    
    // Ghi kết quả vào ô D2 trên sheet 'backend'
    writeResponseToSheet('backend', 'C2', extendedTranscription);
  } catch (error) {
    Logger.log('Lỗi khi thực hiện testExtendTranscriptionSegment: ' + error.message);
    writeResponseToSheet('backend', 'C2', 'Lỗi: ' + error.message);
  }
}

