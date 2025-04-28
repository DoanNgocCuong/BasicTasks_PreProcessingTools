import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import requests
import json

def select_audio_file():
    file_path = filedialog.askopenfilename(
        title="Select an audio file",
        filetypes=[("Audio Files", "*.mp3 *.wav")]
    )
    if file_path:
        file_path_var.set(file_path)

def speech_to_text_and_assign_roles():
    file_path = file_path_var.get()
    if not file_path:
        messagebox.showwarning("Warning", "Please select an audio file first.")
        return

    # Step 1: Speech to Text
    try:
        stt_url = "http://42.96.42.156:6112/api/v1/asr/audio"
        stt_token = "su-ewiuwernmvf1ifmdsafajkdfaiwwe"
        headers = {"accept": "application/json"}
        files = {
            "token": (None, stt_token),
            "language": (None, "vi"),
            "file": open(file_path, "rb")
        }
        
        stt_response = requests.post(stt_url, headers=headers, files=files)
        stt_response.raise_for_status()
        stt_result = stt_response.json()
        if stt_result["success"]:
            transcription = stt_result['result']['text']
            transcription_text.delete(1.0, tk.END)
            transcription_text.insert(tk.END, transcription)
            print("Transcription:", transcription)
        else:
            messagebox.showerror("Error", f"Error: {stt_result['msg']}")
            return
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Request failed: {e}")
        return

    # Step 2: Assign Roles
    try:
        openai_url = "https://api.openai.com/v1/chat/completions"
        openai_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer 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"
        }
        openai_data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "user",
                    "content": f"Phân vai các đoạn hội thoại giữa 'Nhân viên bán hàng' và 'Khách hàng':\n\n{transcription}"
                }
            ]
        }
        
        openai_response = requests.post(openai_url, headers=openai_headers, data=json.dumps(openai_data))
        openai_response.raise_for_status()
        openai_result = openai_response.json()
        if 'choices' in openai_result and len(openai_result['choices']) > 0:
            assigned_roles = openai_result['choices'][0]['message']['content']
            roles_text.delete(1.0, tk.END)
            roles_text.insert(tk.END, assigned_roles)
            print("Assigned Roles:", assigned_roles)
        else:
            messagebox.showerror("Error", "No response from OpenAI.")
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Request failed: {e}")

# Create the main window
root = tk.Tk()
root.title("Speech to Text and Assign Roles")

file_path_var = tk.StringVar()

# Create and place widgets
select_button = tk.Button(root, text="Chọn audio", command=select_audio_file)
select_button.pack(pady=10)

process_button = tk.Button(root, text="Speech to Text và Phân vai", command=speech_to_text_and_assign_roles)
process_button.pack(pady=10)

transcription_text = ScrolledText(root, wrap=tk.WORD, width=80, height=10)
transcription_text.pack(pady=10)

roles_text = ScrolledText(root, wrap=tk.WORD, width=80, height=10)
roles_text.pack(pady=10)

file_label = tk.Label(root, textvariable=file_path_var)
file_label.pack(pady=10)

# Start the main event loop
root.mainloop()
