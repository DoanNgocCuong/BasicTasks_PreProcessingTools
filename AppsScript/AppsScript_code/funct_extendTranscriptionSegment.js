// Core function
/**
 * Extends a segment of the transcription by a specified time.
 * @param {string} transcriptionStr - Full transcription of the video as a multiline string.
 * @param {Object} sections - Đối tượng chứa các phần như warm_up, lead-in, wrap_up.
 * @param {string} key - Tên của phần mà bạn muốn mở rộng đoạn transcription.
 * @param {Number} extensionTime - Desired time extension on both sides (in seconds). Default is 120 seconds.
 * @returns {string} - The extended transcription within the new time range.
 */
function extendTranscriptionSegment(transcriptionStr, sections, key, extensionTime = 120) {
  // Lấy start và end thời gian tính bằng giây từ sections JSON dựa trên key
  const { start, end } = getStartEndTimes(sections, key);

  // Tính toán thời gian bắt đầu và kết thúc mới với phần mở rộng
  const newStartTime = Math.max(0, start - extensionTime);
  const newEndTime = end + extensionTime;

  // Chuyển đổi chuỗi transcription thành mảng các đối tượng
  const transcription = parseTranscription(transcriptionStr);

  // Lọc các dòng transcription trong khoảng thời gian mới
  const extendedTranscription = transcription.filter(item => 
    item.timestamp >= newStartTime && item.timestamp <= newEndTime
  );

  // Chuyển đổi mảng kết quả thành chuỗi
  return extendedTranscription.map(item => item.originalLine).join('\n');
}





/**
 * Hàm để lấy thời gian bắt đầu (start) và kết thúc (end) từ một phần cụ thể trong đối tượng.
 * @param {Object} sections - Đối tượng chứa các phần như warm_up, lead-in, wrap_up.
 * @param {string} key - Tên của phần mà bạn muốn lấy start và end (ví dụ: "warm_up", "lead-in", "wrap_up").
 * @returns {Object} - Đối tượng chứa start và end của phần được chỉ định, tính bằng giây.
 */
function getStartEndTimes(sections, key) {
  Logger.log('Sections Object:', sections);
  Logger.log('Key:', key);

  // Kiểm tra xem đối tượng sections có chứa key hay không
  if (sections.hasOwnProperty(key)) {
    const section = sections[key];
    const { start, end } = section;

    if (start && end) {
      return {
        start: convertTimeToSeconds(start),
        end: convertTimeToSeconds(end)
      };
    } else {
      throw new Error(`Start hoặc end không hợp lệ cho phần: ${key}`);
    }
  } else {
    throw new Error(`Phần "${key}" không tồn tại trong đối tượng.`);
  }
}




/**
 * Chuyển đổi chuỗi transcription thành mảng các đối tượng.
 * @param {string} transcriptionStr - Chuỗi transcription đa dòng.
 * @returns {Array} - Mảng các đối tượng với timestamp (giây), text, và dòng gốc.
 */
function parseTranscription(transcriptionStr) {
  const lines = transcriptionStr.trim().split('\n');
  return lines.map(line => {
    const timestampMatch = line.match(/\[(\d{2}:\d{2}:\d{2})\]/);
    if (timestampMatch) {
      const timestampStr = timestampMatch[1];
      const timestampSeconds = convertTimeToSeconds(timestampStr);
      const text = line.replace(/\[\d{2}:\d{2}:\d{2}\]\s*/, '');
      return {
        timestamp: timestampSeconds,
        text: text,
        originalLine: line
      };
    }
    return null;
  }).filter(item => item !== null);
}


/**
 * Chuyển đổi chuỗi thời gian "hh:mm:ss" thành giây.
 * @param {string} timeStr - Chuỗi thời gian định dạng "hh:mm:ss".
 * @returns {Number} - Thời gian tính bằng giây.
 */
function convertTimeToSeconds(timeStr) {
  const [hours, minutes, seconds] = timeStr.split(':').map(Number);
  return hours * 3600 + minutes * 60 + seconds;
}
