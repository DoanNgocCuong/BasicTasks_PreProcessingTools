function runExtendWarmUp() {
  // Lấy dữ liệu từ các sheet tương ứng
  var transcriptionStr = getDataFromSheet('backend', 'A2');
  var sectionsStr = getDataFromSheet('backend', 'B2');
  
  var sections = parseSections(sectionsStr);
  if (sections === null) return;
  
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


// Parse sectionsStr to a JSON object
function parseSections(sectionsStr) {
  try {
    var sections = JSON.parse(sectionsStr);
    Logger.log('Parsed sections object: ' + JSON.stringify(sections));
    return sections;
  } catch (e) {
    Logger.log('Lỗi khi parsing JSON từ sections: ' + e.message);
    writeResponseToSheet('backend', 'D2', 'Lỗi: Không thể parse JSON từ dữ liệu sections');
    return null;
  }
}