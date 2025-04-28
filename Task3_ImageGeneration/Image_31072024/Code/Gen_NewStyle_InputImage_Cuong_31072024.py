#This is an example that uses the websockets api to know when a prompt execution is done
#Once the prompt execution is done it downloads the images using the /history endpoint

import websocket # websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
import json
import urllib.request
import urllib.parse



server_address = "103.253.20.13:7860"
client_id = str(uuid.uuid4())

def queue_prompt(prompt):
    print("Queueing prompt...")
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    response = json.loads(urllib.request.urlopen(req).read())
    print(f"Prompt queued. Prompt ID: {response['prompt_id']}")
    return response

def get_image(filename, subfolder, folder_type):
    print(f"Fetching image: {filename}")
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
        print("Image fetched successfully")
        return response.read()

def get_history(prompt_id):
    print(f"Fetching history for prompt ID: {prompt_id}")
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        history = json.loads(response.read())
        print("History fetched successfully")
        return history
def get_images(ws, prompt):
    print("Starting image generation process...")
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_images = {}
    while True:
        print("Waiting for WebSocket message...")
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            print(f"Received message: {message['type']}")
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    print("Execution completed")
                    break
        else:
            print("Received binary data (preview)")

    print("Fetching generated images...")
    history = get_history(prompt_id)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        if 'images' in node_output:
            print(f"Processing images for node {node_id}")
            images_output = []
            for image in node_output['images']:
                image_data = get_image(image['filename'], image['subfolder'], image['type'])
                images_output.append(image_data)
            output_images[node_id] = images_output

    print("Image generation process completed")
    return output_images



prompt_text = json.dumps(json.loads('''
{
  "1": {
    "inputs": {
      "weight": 0.9,
      "weight_type": "style transfer",
      "combine_embeds": "concat",
      "start_at": 0,
      "end_at": 1,
      "embeds_scaling": "K+V",
      "model": [
        "5",
        0
      ],
      "ipadapter": [
        "5",
        1
      ],
      "image": [
        "3",
        0
      ],
      "clip_vision": [
        "4",
        0
      ]
    },
    "class_type": "IPAdapterAdvanced",
    "_meta": {
      "title": "IPAdapter Advanced"
    }
  },
  "2": {
    "inputs": {
      "ckpt_name": "dreamshaperXL_lightningDPMSDE.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint"
    }
  },
  "3": {
    "inputs": {
      "image": "InputImag.png",
      "upload": "image"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "Load Image"
    }
  },
  "4": {
    "inputs": {
      "clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
    },
    "class_type": "CLIPVisionLoader",
    "_meta": {
      "title": "Load CLIP Vision"
    }
  },
  "5": {
    "inputs": {
      "preset": "PLUS (high strength)",
      "model": [
        "2",
        0
      ]
    },
    "class_type": "IPAdapterUnifiedLoader",
    "_meta": {
      "title": "IPAdapter Unified Loader"
    }
  },
  "6": {
    "inputs": {
      "seed": 359621462251463,
      "steps": 30,
      "cfg": 6,
      "sampler_name": "dpmpp_2m",
      "scheduler": "karras",
      "denoise": 1,
      "model": [
        "1",
        0
      ],
      "positive": [
        "8",
        0
      ],
      "negative": [
        "9",
        0
      ],
      "latent_image": [
        "7",
        0
      ]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "KSampler"
    }
  },
  "7": {
    "inputs": {
      "width": 1512,
      "height": 1008,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  },
  "8": {
    "inputs": {
      "text": "commercial illustration, flat illustration, animation still, corporate animation style, wikihow illustration, quality illustration, 2d animation, professional illustration, cartoon still, digital 2d animation, cg animation, animated still, illustrations, cartoon illustration, high quality, color block, 4k, simple detail, simple background, (flat illustration:1.2), no lines, (vector illustration:1.3), adobe illustration, Sam and Taylor catching up during a class reunion, both smiling and engaged in conversation, a few 2-3 other classmates in the classroom background, simple and minimalist scene, focus on their friendly interaction, (simple color:1.4), (flat style:1.4),(flat illustration style:1.4), <lora:Flat_Corporate_Style:1>, <lora:Fresh Ideas@pixar style_SDXL.safetensors:0.7>, <lora:Flat style:1.4> Flat style",
      "clip": [
        "2",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "9": {
    "inputs": {
      "text": "detailed, deformed, low quality, intricate, realistic, photo, deformed hands, extra fingers, fused fingers, missing fingers, extra limbs, deformed feet, extra toes, missing toes, malformed limbs, disproportionate limbs, distorted anatomy, anatomical errors",
      "clip": [
        "2",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "10": {
    "inputs": {
      "samples": [
        "6",
        0
      ],
      "vae": [
        "2",
        2
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "12": {
    "inputs": {
      "anything": [
        "10",
        0
      ]
    },
    "class_type": "easy cleanGpuUsed",
    "_meta": {
      "title": "Clean GPU Used"
    }
  },
  "15": {
    "inputs": {
      "guide_size": 512,
      "guide_size_for": true,
      "max_size": 1024,
      "seed": 453642018727810,
      "steps": 20,
      "cfg": 8,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 0.5,
      "feather": 5,
      "noise_mask": true,
      "force_inpaint": true,
      "bbox_threshold": 0.5,
      "bbox_dilation": 10,
      "bbox_crop_factor": 3,
      "sam_detection_hint": "center-1",
      "sam_dilation": 0,
      "sam_threshold": 0.93,
      "sam_bbox_expansion": 0,
      "sam_mask_hint_threshold": 0.7,
      "sam_mask_hint_use_negative": "False",
      "drop_size": 10,
      "wildcard": "",
      "cycle": 1,
      "inpaint_model": false,
      "noise_mask_feather": 20,
      "image": [
        "10",
        0
      ],
      "model": [
        "16",
        0
      ],
      "clip": [
        "16",
        1
      ],
      "vae": [
        "16",
        2
      ],
      "positive": [
        "16",
        3
      ],
      "negative": [
        "16",
        4
      ],
      "bbox_detector": [
        "19",
        0
      ],
      "sam_model_opt": [
        "18",
        0
      ],
      "segm_detector_opt": [
        "17",
        1
      ]
    },
    "class_type": "FaceDetailer",
    "_meta": {
      "title": "FaceDetailer"
    }
  },
  "16": {
    "inputs": {
      "basic_pipe": [
        "20",
        0
      ]
    },
    "class_type": "FromBasicPipe",
    "_meta": {
      "title": "FromBasicPipe"
    }
  },
  "17": {
    "inputs": {
      "model_name": "segm/person_yolov8m-seg.pt"
    },
    "class_type": "UltralyticsDetectorProvider",
    "_meta": {
      "title": "UltralyticsDetectorProvider"
    }
  },
  "18": {
    "inputs": {
      "model_name": "sam_vit_b_01ec64.pth",
      "device_mode": "AUTO"
    },
    "class_type": "SAMLoader",
    "_meta": {
      "title": "SAMLoader (Impact)"
    }
  },
  "19": {
    "inputs": {
      "model_name": "bbox/face_yolov8m.pt"
    },
    "class_type": "UltralyticsDetectorProvider",
    "_meta": {
      "title": "UltralyticsDetectorProvider"
    }
  },
  "20": {
    "inputs": {
      "model": [
        "2",
        0
      ],
      "clip": [
        "2",
        1
      ],
      "vae": [
        "2",
        2
      ],
      "positive": [
        "8",
        0
      ],
      "negative": [
        "9",
        0
      ]
    },
    "class_type": "ToBasicPipe",
    "_meta": {
      "title": "ToBasicPipe"
    }
  },
  "21": {
    "inputs": {
      "images": [
        "15",
        0
      ]
    },
    "class_type": "PreviewImage",
    "_meta": {
      "title": "Preview Image"
    }
  }
}
'''))
prompt = json.loads(prompt_text)

#### SET THÊM 1 BƯỚC QUAN TRỌNG ĐỂ XỬ LÝ ẢNH ĐẦU VÀO
from PIL import Image
import io

def compress_image(image_path, quality=85):
    img = Image.open(image_path)
    img_io = io.BytesIO()
    img.save(img_io, format='JPEG', quality=quality)
    img_io.seek(0)
    return img_io.getvalue()

def image_to_base64(image_path):
    compressed_image = compress_image(image_path)
    return base64.b64encode(compressed_image).decode('utf-8')

print(json.dumps(prompt, indent=2))

#set the text prompt for our positive CLIPTextEncode
prompt["8"]["inputs"]["text"] = "high quality, color block, 4k, simple detail, simple background, (flat illustration:1.2), no lines, (vector illustration:1.3), adobe illustration,a woman, sitting in office, (simple color:1.4), (flat style:1.4),(flat illustration style:1.4), <lora:Flat_Corporate_Style:1>, <lora:Fresh Ideas@pixar style_SDXL.safetensors:0.7>, <lora:Flat style:1.4> Flat style"
prompt["6"]["inputs"]["seed"] = 435347645

# In ra prompt để kiểm tra
import requests

def queue_prompt(prompt):
    print("Queueing prompt...")
    p = {"prompt": prompt, "client_id": client_id}
    url = f"http://{server_address}/prompt"
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, json=p, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if hasattr(e, 'response'):
            print(f"Response content: {e.response.content}")
        raise
    
# from websocket import create_connection

ws = websocket.WebSocket()
print(f"Connecting to WebSocket: ws://{server_address}/ws?clientId={client_id}")
ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
print("WebSocket connected")

print("Starting image generation...")
images = get_images(ws, prompt)

print("Saving generated images...")
# Lấy thư mục hiện tại
import os
current_directory = os.getcwd()
print(f"Current working directory: {current_directory}")

for node_id in images:
    for i, image_data in enumerate(images[node_id]):
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(image_data))
        filename = f"generated_image_node{node_id}_{i}.png"
        full_path = os.path.join(current_directory, filename)
        image.save(full_path)
        print(f"Saved image: {full_path}")

print("Script execution completed")
print(f"All images have been saved in the directory: {current_directory}")
print("List of generated files:")
for file in os.listdir(current_directory):
    if file.startswith("generated_image_node"):
        print(f" - {file}")