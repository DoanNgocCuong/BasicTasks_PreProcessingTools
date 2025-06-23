# @DoanNgocCuong
"""
# QUan trọng nhất vẫn là model nhận diện trẻ em và người lớn. Code trêển khai cái này trước. Input là 1 folder trong đó có nhêều audio (dạng .wav)
=> Output mong muốn là: Folder output chứa
1. Folder trẻ em 
2. Folder người lớn 
3. File excel gồm tên file và label (trẻ em/người lớn)
4. File results.txt (đánh giá Precision, Recall)

Note: Dùng pathlib đi 
File code để ngang bằng vị trí với folder: input và folder output File code để ngang bằng vị trí với folder: input và folder output

---

Mỗi file audio .wav sẽ được đưa qua model wav2vec2 để dự đoán nhãn child/adult.
Nếu dự đoán là "child" với độ tự tin (confidence) lớn hơn 0.7 thì file sẽ được chép vào folder "child", ngược lại vào "adult".
Tất cả kết quả được ghi vào file Excel.
Nếu có file groundtruth, code sẽ tính Precision/Recall và ghi ra file results.txt.
"""
"""
Hệ thống phân loại giọng nói trẻ em/người lớn
Author: @DoanNgocCuong
Description: Phân loại file audio .wav thành trẻ em và người lớn sử dụng wav2vec2
Model: audeering/wav2vec2-large-robust-24-ft-age-gender
"""

import torchaudio
import torch
import torch.nn as nn
import librosa
import numpy as np
import warnings
from transformers import Wav2Vec2Processor
from transformers.models.wav2vec2.modeling_wav2vec2 import (
    Wav2Vec2Model,
    Wav2Vec2PreTrainedModel,
)
from pathlib import Path
import pandas as pd
import shutil
from sklearn.metrics import precision_score, recall_score, classification_report, confusion_matrix
import logging
from tqdm import tqdm

# Tắt warnings không cần thiết
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ModelHead(nn.Module):
    """Classification head."""

    def __init__(self, config, num_labels):
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.dropout = nn.Dropout(config.final_dropout)
        self.out_proj = nn.Linear(config.hidden_size, num_labels)

    def forward(self, features, **kwargs):
        x = features
        x = self.dropout(x)
        x = self.dense(x)
        x = torch.tanh(x)
        x = self.dropout(x)
        x = self.out_proj(x)
        return x


class AgeGenderModel(Wav2Vec2PreTrainedModel):
    """Speech age and gender classifier."""

    def __init__(self, config):
        super().__init__(config)
        self.config = config
        self.wav2vec2 = Wav2Vec2Model(config)
        self.age = ModelHead(config, 1)
        self.gender = ModelHead(config, 3)
        self.init_weights()

    def forward(self, input_values):
        outputs = self.wav2vec2(input_values)
        hidden_states = outputs[0]
        hidden_states = torch.mean(hidden_states, dim=1)
        logits_age = self.age(hidden_states)
        logits_gender = torch.softmax(self.gender(hidden_states), dim=1)
        return hidden_states, logits_age, logits_gender


class AudioClassifier:
    def __init__(self, model_name="audeering/wav2vec2-large-robust-24-ft-age-gender", 
                 child_threshold=0.5, age_threshold=0.3):
        """
        Khởi tạo classifier với model và ngưỡng confidence
        
        Args:
            model_name: Tên model trên Hugging Face
            child_threshold: Ngưỡng xác suất để phân loại trẻ em (child)
            age_threshold: Ngưỡng tuổi để phân loại (0.3 ~ 30 tuổi)
        """
        self.model_name = model_name
        self.child_threshold = child_threshold
        self.age_threshold = age_threshold
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Sử dụng device: {self.device}")
        
        # Load model và processor
        try:
            logger.info("Đang tải model...")
            self.processor = Wav2Vec2Processor.from_pretrained(model_name)
            self.model = AgeGenderModel.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            logger.info("Tải model thành công!")
        except Exception as e:
            logger.error(f"Lỗi khi tải model: {e}")
            raise
        
        # Labels: [female, male, child]
        self.gender_labels = ['female', 'male', 'child']
        
    def preprocess_audio(self, audio_path, target_sr=16000):
        """
        Tiền xử lý file audio
        """
        try:
            # Sử dụng librosa để đọc audio
            speech_array, original_sr = librosa.load(audio_path, sr=None)
            
            # Resample nếu cần
            if original_sr != target_sr:
                speech_array = librosa.resample(speech_array, orig_sr=original_sr, target_sr=target_sr)
            
            # Normalize audio
            if np.max(np.abs(speech_array)) > 0:
                speech_array = speech_array / np.max(np.abs(speech_array))
            
            return speech_array.astype(np.float32), target_sr
        except Exception as e:
            logger.error(f"Lỗi khi xử lý audio {audio_path}: {e}")
            return None, None
    
    def predict(self, audio_path):
        """
        Dự đoán tuổi và giới tính cho một file audio
        """
        speech_array, sampling_rate = self.preprocess_audio(audio_path)
        if speech_array is None:
            return None, None, None, "error"
        
        try:
            # Process audio
            inputs = self.processor(speech_array, sampling_rate=sampling_rate)
            input_values = inputs['input_values'][0]
            input_values = input_values.reshape(1, -1)
            input_values = torch.from_numpy(input_values).to(self.device)
            
            # Prediction
            with torch.no_grad():
                hidden_states, age_logits, gender_probs = self.model(input_values)
                
                # Age prediction (0-1 scale, 0=0 years, 1=100 years)
                age_normalized = float(age_logits.squeeze())
                age_years = age_normalized * 100  # Convert to years
                
                # Gender prediction probabilities [female, male, child]
                gender_probs = gender_probs.squeeze().cpu().numpy()
                
                return age_normalized, age_years, gender_probs, "success"
                
        except Exception as e:
            logger.error(f"Lỗi khi dự đoán {audio_path}: {e}")
            return None, None, None, "error"
    
    def classify_age_group(self, age_normalized, gender_probs):
        """
        Phân loại thành trẻ em hoặc người lớn
        
        Logic:
        1. Nếu gender_probs[2] (child) > child_threshold -> child
        2. Hoặc nếu age_normalized < age_threshold -> child  
        3. Ngược lại -> adult
        """
        child_prob = gender_probs[2] if gender_probs is not None else 0
        
        # Kiểm tra xác suất child
        if child_prob > self.child_threshold:
            return "child", child_prob
        
        # Hoặc kiểm tra tuổi
        if age_normalized is not None and age_normalized < self.age_threshold:
            return "child", age_normalized
        
        return "adult", 1 - child_prob


def main():
    # Đường dẫn folder input/output
    input_folder = Path('./input')
    output_folder = Path('./output')
    child_folder = output_folder / 'child'
    adult_folder = output_folder / 'adult'
    
    # Kiểm tra folder input
    if not input_folder.exists():
        logger.error(f"Folder input không tồn tại: {input_folder}")
        print("❌ Tạo folder 'input' và đặt các file .wav vào đó!")
        return
    
    # Tạo các folder output
    output_folder.mkdir(exist_ok=True)
    child_folder.mkdir(exist_ok=True)
    adult_folder.mkdir(exist_ok=True)
    
    # Khởi tạo classifier
    # Bạn có thể điều chỉnh các ngưỡng này:
    # - child_threshold: xác suất child > ngưỡng này -> child
    # - age_threshold: tuổi < ngưỡng này (0.3 = 30 tuổi) -> child
    classifier = AudioClassifier(child_threshold=0.4, age_threshold=0.25)
    
    # Tìm tất cả file wav
    wav_files = list(input_folder.glob('*.wav'))
    if not wav_files:
        logger.error("Không tìm thấy file .wav nào trong folder input")
        print("❌ Không tìm thấy file .wav nào trong folder 'input'")
        return
    
    logger.info(f"Tìm thấy {len(wav_files)} file .wav")
    
    # Xử lý từng file
    results = []
    success_count = 0
    error_count = 0
    
    for wav_file in tqdm(wav_files, desc="🎵 Đang phân loại audio"):
        # Dự đoán
        age_norm, age_years, gender_probs, status = classifier.predict(wav_file)
        
        if status == "error":
            error_count += 1
            results.append({
                'filename': wav_file.name,
                'age_normalized': 'error',
                'age_years': 'error',
                'female_prob': 'error',
                'male_prob': 'error', 
                'child_prob': 'error',
                'final_label': 'error',
                'confidence': 0.0,
                'status': 'error'
            })
            continue
        
        # Phân loại age group
        final_label, confidence = classifier.classify_age_group(age_norm, gender_probs)
        
        # Copy file vào folder tương ứng
        try:
            if final_label == "child":
                shutil.copy2(wav_file, child_folder / wav_file.name)
            else:
                shutil.copy2(wav_file, adult_folder / wav_file.name)
            success_count += 1
        except Exception as e:
            logger.error(f"Lỗi khi copy file {wav_file.name}: {e}")
            final_label = "error"
            error_count += 1
        
        # Lưu kết quả
        results.append({
            'filename': wav_file.name,
            'age_normalized': round(age_norm, 4) if age_norm is not None else 'N/A',
            'age_years': round(age_years, 1) if age_years is not None else 'N/A',
            'female_prob': round(gender_probs[0], 4) if gender_probs is not None else 'N/A',
            'male_prob': round(gender_probs[1], 4) if gender_probs is not None else 'N/A',
            'child_prob': round(gender_probs[2], 4) if gender_probs is not None else 'N/A',
            'final_label': final_label,
            'confidence': round(confidence, 4),
            'status': 'success' if final_label != 'error' else 'error'
        })
    
    # Xuất kết quả ra Excel
    df = pd.DataFrame(results)
    excel_path = output_folder / 'classification_results.xlsx'
    
    try:
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Results', index=False)
            
            # Thêm sheet thống kê
            child_count = len(df[df['final_label'] == 'child'])
            adult_count = len(df[df['final_label'] == 'adult'])
            
            stats_df = pd.DataFrame({
                'Metric': [
                    'Total Files', 'Success', 'Error', 'Child', 'Adult', 
                    'Success Rate', 'Child Rate', 'Adult Rate'
                ],
                'Value': [
                    len(wav_files),
                    success_count,
                    error_count,
                    child_count,
                    adult_count,
                    f"{(success_count/len(wav_files)*100):.2f}%",
                    f"{(child_count/len(wav_files)*100):.2f}%",
                    f"{(adult_count/len(wav_files)*100):.2f}%"
                ]
            })
            stats_df.to_excel(writer, sheet_name='Statistics', index=False)

            # Thêm sheet cho child, adult, all
            df_child = df[df['final_label'] == 'child']
            df_adult = df[df['final_label'] == 'adult']
            df_child.to_excel(writer, sheet_name='child', index=False)
            df_adult.to_excel(writer, sheet_name='adult', index=False)
            df.to_excel(writer, sheet_name='all', index=False)
        
        logger.info(f"✅ Đã lưu kết quả vào: {excel_path}")
    except Exception as e:
        logger.error(f"Lỗi khi xuất Excel: {e}")
    
    # Tính Precision/Recall nếu có groundtruth
    groundtruth_path = input_folder / 'groundtruth.csv'
    results_txt_path = output_folder / 'results.txt'
    
    try:
        with open(results_txt_path, 'w', encoding='utf-8') as f:
            f.write("=== KẾT QUẢ PHÂN LOẠI AUDIO TRẺ EM/NGƯỜI LỚN ===\n\n")
            f.write(f"📊 Model: {classifier.model_name}\n")
            f.write(f"🎯 Ngưỡng Child Probability: {classifier.child_threshold}\n")
            f.write(f"🎯 Ngưỡng Age: {classifier.age_threshold} ({classifier.age_threshold*100} tuổi)\n\n")
            
            f.write("📈 THỐNG KÊ TỔNG QUÁT:\n")
            f.write(f"Tổng số file: {len(wav_files)}\n")
            f.write(f"Thành công: {success_count}\n")
            f.write(f"Lỗi: {error_count}\n")
            f.write(f"Trẻ em: {child_count}\n")
            f.write(f"Người lớn: {adult_count}\n")
            f.write(f"Tỷ lệ thành công: {(success_count/len(wav_files)*100):.2f}%\n")
            f.write(f"Tỷ lệ trẻ em: {(child_count/len(wav_files)*100):.2f}%\n")
            f.write(f"Tỷ lệ người lớn: {(adult_count/len(wav_files)*100):.2f}%\n\n")
            
            if groundtruth_path.exists():
                try:
                    gt_df = pd.read_csv(groundtruth_path)
                    # Merge với kết quả dự đoán
                    merged = df.merge(gt_df, on='filename', how='inner')
                    
                    if len(merged) > 0:
                        # Chỉ tính với các sample thành công
                        valid_merged = merged[merged['status'] == 'success']
                        
                        if len(valid_merged) > 0:
                            y_true = valid_merged['true_label']
                            y_pred = valid_merged['final_label']
                            
                            # Tính metrics
                            labels = ['adult', 'child']
                            precision = precision_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
                            recall = recall_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
                            
                            f.write("🎯 ĐÁNH GIÁ VỚI GROUNDTRUTH:\n")
                            f.write(f"Số sample có groundtruth: {len(valid_merged)}\n")
                            f.write(f"Precision (Adult): {precision[0]:.4f}\n")
                            f.write(f"Recall (Adult): {recall[0]:.4f}\n")
                            f.write(f"Precision (Child): {precision[1]:.4f}\n")
                            f.write(f"Recall (Child): {recall[1]:.4f}\n\n")
                            
                            # Classification report
                            f.write("📋 Classification Report:\n")
                            f.write(classification_report(y_true, y_pred, target_names=labels))
                            f.write("\n")
                            
                            # Confusion Matrix
                            f.write("🔢 Confusion Matrix:\n")
                            f.write("    Predicted\n")
                            f.write("    Adult Child\n")
                            cm = confusion_matrix(y_true, y_pred, labels=labels)
                            f.write(f"Adult  {cm[0][0]:3d}   {cm[0][1]:3d}\n")
                            f.write(f"Child  {cm[1][0]:3d}   {cm[1][1]:3d}\n")
                            f.write("Actual\n\n")
                        else:
                            f.write("❌ Không có sample thành công để đánh giá.\n")
                    else:
                        f.write("❌ Không có sample nào match với groundtruth.\n")
                        
                except Exception as e:
                    f.write(f"❌ Lỗi khi xử lý groundtruth: {e}\n")
            else:
                f.write("📝 HƯỚNG DẪN TẠO GROUNDTRUTH:\n")
                f.write("Để đánh giá độ chính xác, tạo file groundtruth.csv với format:\n")
                f.write("filename,true_label\n")
                f.write("audio1.wav,child\n")
                f.write("audio2.wav,adult\n\n")
        
        logger.info(f"✅ Đã lưu báo cáo vào: {results_txt_path}")
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo: {e}")
    
    # In kết quả tổng kết
    print("\n" + "="*60)
    print("🎵 KẾT QUẢ PHÂN LOẠI GIỌNG NÓI TRẺ EM/NGƯỜI LỚN")
    print("="*60)
    print(f"📁 Tổng số file xử lý: {len(wav_files)}")
    print(f"✅ Thành công: {success_count}")
    print(f"❌ Lỗi: {error_count}")
    print(f"👶 Trẻ em: {child_count} ({(child_count/len(wav_files)*100):.1f}%)")
    print(f"👨 Người lớn: {adult_count} ({(adult_count/len(wav_files)*100):.1f}%)")
    print(f"📊 Tỷ lệ thành công: {(success_count/len(wav_files)*100):.2f}%")
    print("\n📂 Các file output:")
    print(f"   📁 {child_folder} - Chứa {child_count} file trẻ em")
    print(f"   📁 {adult_folder} - Chứa {adult_count} file người lớn") 
    print(f"   📊 {excel_path} - Kết quả chi tiết")
    print(f"   📝 {results_txt_path} - Báo cáo đánh giá")
    print("="*60)
    
    if child_count == 0:
        print("⚠️  CẢNH BÁO: Không phát hiện file trẻ em nào!")
        print("💡 Thử giảm child_threshold hoặc tăng age_threshold trong code")
    elif adult_count == 0:
        print("⚠️  CẢNH BÁO: Không phát hiện file người lớn nào!")
        print("💡 Thử tăng child_threshold hoặc giảm age_threshold trong code")


if __name__ == "__main__":
    main()
