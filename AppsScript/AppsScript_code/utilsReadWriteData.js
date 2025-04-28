


function testCopy(){
  copyDataBetweenSheets('used', 'B2', 'Output mẫu 1', 'E3');
  copyDataBetweenSheets('used', 'D2', 'Output mẫu 1', 'F3');
  copyDataBetweenSheets('used', 'D3', 'Output mẫu 1', 'F4');
  copyDataBetweenSheets('used', 'D4', 'Output mẫu 1', 'F5');
}

/**
 * Lấy dữ liệu từ một ô cụ thể trong một sheet cụ thể.
 * @param {string} sheetName - Tên của sheet.
 * @param {string} cellAddress - Địa chỉ của ô (ví dụ: "A1").
 * @returns {string} - Giá trị của ô.
 */
function getDataFromSheet(sheetName, cellAddress) {
  // Lấy bảng tính hiện tại
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(sheetName);
  
  // Lấy giá trị của ô cụ thể
  var cellValue = sheet.getRange(cellAddress).getValue();
  
  // Trả về giá trị của ô
  return cellValue;
}


/**
 * Ghi phản hồi từ OpenAI vào Google Sheets.
 * @param {string} sheetName - Tên sheet để ghi dữ liệu.
 * @param {string} range - Phạm vi ô để ghi dữ liệu (ví dụ: 'A1').
 * @param {string} result - Nội dung phản hồi từ mô hình.
 */
function writeResponseToSheet(sheetName, range, result) {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = spreadsheet.getSheetByName(sheetName);
  
  if (!sheet) {
    throw new Error('Sheet "' + sheetName + '" không tồn tại.');
  }
  
  sheet.getRange(range).setValue(result);
  Logger.log('Đã ghi phản hồi vào sheet "' + sheetName + '" ô ' + range);
}




/**
 * Sao chép dữ liệu từ một ô trên sheet này sang một ô trên sheet khác.
 * @param {string} sourceSheetName - Tên của sheet nguồn.
 * @param {string} sourceCell - Địa chỉ của ô nguồn (ví dụ: 'A1').
 * @param {string} targetSheetName - Tên của sheet đích.
 * @param {string} targetCell - Địa chỉ của ô đích (ví dụ: 'B1').
 */
function copyDataBetweenSheets(sourceSheetName, sourceCell, targetSheetName, targetCell) {
  // Lấy bảng tính hiện tại
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();

  // Lấy sheet nguồn và sheet đích
  var sourceSheet = spreadsheet.getSheetByName(sourceSheetName);
  var targetSheet = spreadsheet.getSheetByName(targetSheetName);

  if (!sourceSheet) {
    throw new Error('Sheet nguồn "' + sourceSheetName + '" không tồn tại.');
  }
  
  if (!targetSheet) {
    throw new Error('Sheet đích "' + targetSheetName + '" không tồn tại.');
  }

  // Lấy giá trị của ô nguồn
  var sourceValue = sourceSheet.getRange(sourceCell).getValue();

  // Ghi giá trị vào ô đích
  targetSheet.getRange(targetCell).setValue(sourceValue);

  Logger.log('Đã sao chép dữ liệu từ sheet "' + sourceSheetName + '" ô ' + sourceCell + 
             ' sang sheet "' + targetSheetName + '" ô ' + targetCell);
}


