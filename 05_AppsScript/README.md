### README.md 
# README: Overview of Functions

## CHẤM ĐIỂM VIDEO MENTOR GIẢNG:  
Finish80% bài chấm điểm Video Mentor từ Transcription gồm 3 bước chính: 
1. Detect: <prompting>
2. Extend: <code backend>
3. SugScoring: <prompting>

## Purpose
This project processes transcription data using Google Sheets and OpenAI API to detect, extend, and score specific sections (e.g., warm-up, lead-in, wrap-up). It reads transcription data, sends it to OpenAI, and writes the results back to Google Sheets.

## Key Scripts

### 1. **`funct_extendTranscriptionSegment.js`**
- Extends a transcription segment by a specified time (default 120 seconds).
- Used in extension scripts like `runExtendAll.js`.

### 2. **`funct_getOpenAIResponse.js`**
- Sends requests to OpenAI API and handles responses.
- Core function for detection and scoring scripts.

### 3. **`utilsReadWriteData.js`**
- Utility functions for reading from and writing to Google Sheets.

### 4. **`config.js`**
- Configuration for API keys, sheet names, and data ranges.

### 5. **`miniRunDetectWarmLeadWrap.js`**
- Detects warm-up, lead-in, and wrap-up sections in transcriptions.

### 6. **`runDetectAll.js`**
- Detects various sections (warm-up, vocab/grammar, ICQs/CCQs) and writes the results to the sheet.

### 7. **`runExtendAll.js`**
- Extends detected sections (warm-up, vocab/grammar, ICQs/CCQs) in the transcription.

### 8. **`runSugScoringAll.js`**
- Scores transcription sections (warm-up, vocab/grammar, ICQs/CCQs) based on OpenAI suggestions.

### 9. **`runAllBackendAndCopyToOutput.js`**
- Runs detection, extension, and scoring for all sections, then copies the results to an output sheet.

## Workflow
1. **Detection**: Detect segments using OpenAI (`runDetectAll.js`).
2. **Extension**: Extend segments' transcription time (`runExtendAll.js`).
3. **Scoring**: Generate suggested scoring for each section (`runSugScoringAll.js`).
4. **Final Output**: Copy all results from backend to the output sheet (`runAllBackendAndCopyToOutput.js`).

## HOW TO RUN THE CODE: 
1. API KEY KO ĐƯỢC PUSH GITHUB: 
=> Need enter API KEY in Google Apps Script: 
2. File .clasp.json cũng KO THỂ PUSH LÊN GITHUB (((chứa ID của repo trên Google Apps Script, nó được tạo khi bạn đăng nhập vào Google Apps Script và chọn "Publish > Deploy as API executable"))).
=> Need enter scriptID in file `.clasp.json` để đồng bộ: VSCode với Google Apps Script. 
// Enter scriptID   

--- 

This project integrates transcription processing with OpenAI, providing flexible functionality for detecting, extending, and scoring sections in transcriptions.