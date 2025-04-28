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
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req =  urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())

def get_images(ws, prompt):
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break #Execution is done
        else:
            continue #previews are binary data

    history = get_history(prompt_id)[prompt_id]
    for o in history['outputs']:
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
            output_images[node_id] = images_output

    return output_images

prompt_text = """
{
  "2": {
    "inputs": {
      "ckpt_name": "MEGACORE.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint"
    }
  },
  "6": {
    "inputs": {
      "seed": 1058362049011654,
      "steps": 30,
      "cfg": 6,
      "sampler_name": "dpmpp_2m",
      "scheduler": "karras",
      "denoise": 1,
      "model": [
        "2",
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
      "width": 1024,
      "height": 1024,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  },
  "8": {
    "inputs": {
      "text": "high quality, color block, 4k, simple detail, simple background, (flat illustration:1.2), no lines, (vector illustration:1.3), adobe illustration, two friends, Kim and Linh, enjoying coffee together, chatting about language learning, (simple color:1.4), (flat style:1.4),(flat illustration style:1.4), <lora:Flat_Corporate_Style:1>, <lora:Fresh Ideas@pixar style_SDXL.safetensors:0.7>, <lora:Flat style:1.4> Flat style",
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
      "text": "detailed, deformed, low quality, intricate, realistic, photo",
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
      "seed": 98361851814072,
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
      "noise_mask_feather": 100,
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
"""

prompt = json.loads(prompt_text)

#set the text prompt for our positive CLIPTextEncode
prompt["8"]["inputs"]["text"] = "high quality, color block, 4k, simple detail, simple background, (flat illustration:1.2), no lines, (vector illustration:1.3), adobe illustration,a woman, sitting in office, (simple color:1.4), (flat style:1.4),(flat illustration style:1.4), <lora:Flat_Corporate_Style:1>, <lora:Fresh Ideas@pixar style_SDXL.safetensors:0.7>, <lora:Flat style:1.4> Flat style"
prompt["6"]["inputs"]["seed"] = 4353476457


# from websocket import create_connection

ws = websocket.WebSocket()
ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
images = get_images(ws, prompt)


#Commented out code to display the output images:

for node_id in images:
    for image_data in images[node_id]:
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(image_data))
        image.save(f"abc_.png")
