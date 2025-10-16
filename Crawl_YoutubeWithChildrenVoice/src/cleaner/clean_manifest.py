import json
import datetime
import re
import os

def clean_manifest(manifest_path):
    # Load the manifest
    with open(manifest_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    records = data.get('records', [])
    changes = []
    
    for i, record in enumerate(records):
        alert_triggered = False
        
        # Check and set video_id
        if 'video_id' not in record:
            record['video_id'] = None
            changes.append(f"Record {i}: Added missing video_id: null")
            alert_triggered = True
        
        # Check and set url
        if 'url' not in record:
            record['url'] = None
            changes.append(f"Record {i}: Added missing url: null")
            alert_triggered = True
        
        # Check and set output_path
        if 'output_path' not in record:
            record['output_path'] = None
            changes.append(f"Record {i}: Added missing output_path: null")
            alert_triggered = True
        
        # Set status to failed if any alert
        if alert_triggered:
            record['status'] = 'failed'
            changes.append(f"Record {i}: Set status to 'failed' due to missing required fields")
        
        # Add missing fields with defaults
        now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        if 'timestamp' not in record:
            record['timestamp'] = now
            changes.append(f"Record {i}: Added timestamp: {now}")
        if 'duration_seconds' not in record:
            record['duration_seconds'] = None
            changes.append(f"Record {i}: Added duration_seconds: null")
        if 'classified' not in record:
            record['classified'] = False
            changes.append(f"Record {i}: Added classified: false")
        if 'classification_timestamp' not in record:
            record['classification_timestamp'] = None
            changes.append(f"Record {i}: Added classification_timestamp: null")
        if 'language_folder' not in record:
            record['language_folder'] = 'unknown'
            changes.append(f"Record {i}: Added language_folder: 'unknown'")
        
        # download_index
        if 'download_index' not in record:
            if record['output_path']:
                filename = os.path.basename(record['output_path'])
                match = re.match(r'(\d+)_', filename)
                if match:
                    record['download_index'] = int(match.group(1))
                    changes.append(f"Record {i}: Added download_index: {record['download_index']}")
                else:
                    record['download_index'] = None
                    changes.append(f"Record {i}: Added download_index: null (could not extract from output_path)")
            else:
                record['download_index'] = None
                changes.append(f"Record {i}: Added download_index: null (output_path is null)")
        
        # title
        if 'title' not in record:
            video_id = record.get('video_id', 'null')
            record['title'] = f"Video {video_id}"
            changes.append(f"Record {i}: Added title: '{record['title']}'")
        
        if 'containing_children_voice' not in record:
            record['containing_children_voice'] = None
            changes.append(f"Record {i}: Added containing_children_voice: null")
        if 'voice_analysis_confident' not in record:
            record['voice_analysis_confident'] = 0.0
            changes.append(f"Record {i}: Added voice_analysis_confident: 0.0")
        if 'uploaded' not in record:
            record['uploaded'] = False
            changes.append(f"Record {i}: Added uploaded: false")
        if 'recovered_at' not in record:
            record['recovered_at'] = now
            changes.append(f"Record {i}: Added recovered_at: {now}")
    
    # Remove duplicates based on video_id
    seen = {}
    new_records = []
    for record in records:
        vid = record.get('video_id')
        if vid not in seen:
            seen[vid] = True
            new_records.append(record)
        else:
            changes.append(f"Removed duplicate record with video_id: {vid}")
    
    data['records'] = new_records
    
    # Print changes
    if changes:
        print("Changes made:")
        for change in changes:
            print(change)
    else:
        print("No changes made.")
    
    # Save back
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    manifest_path = "../../output/final_audio/manifest.json"
    clean_manifest(manifest_path)