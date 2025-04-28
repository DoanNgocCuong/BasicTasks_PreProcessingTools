import os
import json
import uuid
import base64
import urllib.request
import urllib.parse
import requests
import websocket
from PIL import Image
import io
import random
import time
import logging
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from openai import OpenAI

# Cấu hình logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cấu hình API
OPENAI_API_KEY = "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"
server_address = "103.253.20.13:7860"
client_id = str(uuid.uuid4())

# Cấu hình retry
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

client = OpenAI(api_key=OPENAI_API_KEY)

def get_completion(prompt, model="gpt-4", temperature=0):
    try:
        messages = [{"role": "user", "content": prompt}]
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error in get_completion: {e}")
        return None

def gen_prompt_image(user_input):
    prompt = f"""
    You are an expert image prompter, follow midjourney prompt guidance.
    From a phrase: "{user_input}", you will create an image prompt to describe exactly that phrase.

    Prompt template: commercial illustration, flat illustration, animation still, corporate animation style, wikihow illustration, quality illustration, 2d animation, 2 d animation, professional illustration, cartoon still, digital 2d animation, cg animation, animated still, illustrations, cartoon illustration, high quality, color block, 4k, simple detail, simple background, (flat illustration:1.2), no lines, (vector illustration:1.3), adobe illustration,  [description prompt part], (simple color:1.4), (flat style:1.4),(flat illustration style:1.4), <lora:Flat_Corporate_Style:1>, <lora:Fresh Ideas@pixar style_SDXL.safetensors:0.7>, <lora:Flat style:1.4> Flat style 

    Return: Only prompt part of the template, do not include other part.
    """
    response = get_completion(prompt)
    return response

def compress_image(image_path, quality=85):
    img = Image.open(image_path)
    img_io = io.BytesIO()
    img.save(img_io, format='JPEG', quality=quality)
    img_io.seek(0)
    return img_io.getvalue()

def image_to_base64(image_path):
    compressed_image = compress_image(image_path)
    return base64.b64encode(compressed_image).decode('utf-8')

def queue_prompt(prompt):
    logger.info("Queueing prompt...")
    p = {"prompt": prompt, "client_id": client_id}
    url = f"http://{server_address}/prompt"
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = http.post(url, json=p, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.error("Request timed out. Try again later.")
    except requests.exceptions.ConnectionError:
        logger.error("Unable to connect to the server. Check your network connection.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error when sending request: {e}")
    return None

def get_image(filename, subfolder, folder_type):
    logger.info(f"Fetching image: {filename}")
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    try:
        with urllib.request.urlopen(f"http://{server_address}/view?{url_values}") as response:
            logger.info("Image fetched successfully")
            return response.read()
    except Exception as e:
        logger.error(f"Error fetching image: {e}")
        return None

def get_history(prompt_id):
    logger.info(f"Fetching history for prompt ID: {prompt_id}")
    try:
        with urllib.request.urlopen(f"http://{server_address}/history/{prompt_id}") as response:
            history = json.loads(response.read())
            logger.info("History fetched successfully")
            return history
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return None

def connect_websocket():
    max_retries = 3
    for _ in range(max_retries):
        try:
            ws = websocket.WebSocket()
            ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
            logger.info("WebSocket connected successfully")
            return ws
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}. Retrying...")
            time.sleep(5)
    raise Exception("Failed to connect to WebSocket after multiple attempts")
def get_images(ws, prompt):
    logger.info("Starting image generation process...")
    prompt_id = queue_prompt(prompt)
    if prompt_id is None:
        logger.error("Failed to queue prompt")
        return None

    output_images = {}
    while True:
        logger.debug("Waiting for WebSocket message...")
        try:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                logger.debug(f"Received message: {message['type']}")
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id['prompt_id']:
                        logger.info("Execution completed")
                        break
            else:
                logger.debug("Received binary data (preview)")
        except Exception as e:
            logger.error(f"Error receiving WebSocket message: {e}")
            break

    logger.info("Fetching generated images...")
    history = get_history(prompt_id['prompt_id'])
    if history and prompt_id['prompt_id'] in history:
        for node_id in history[prompt_id['prompt_id']]['outputs']:
            node_output = history[prompt_id['prompt_id']]['outputs'][node_id]
            if 'images' in node_output:
                logger.info(f"Processing images for node {node_id}")
                images_output = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    if image_data:
                        images_output.append(image_data)
                output_images[node_id] = images_output

    logger.info("Image generation process completed")
    return output_images
def generate_images(image_name, full_prompt):
    """
    Mặc định: image_name = user_input, full_prompt = full_prompt
    """
    # Load and prepare prompt
    prompt_text = '''
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
          "width": 1024,
          "height": 1024,
          "batch_size": 2
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
    '''
    prompt = json.loads(prompt_text)

    seed_random = random.randint(0, 6000000) + random.randint(0, 100000)
    print(seed_random)

    prompt["8"]["inputs"]["text"] = full_prompt
    prompt["6"]["inputs"]["seed"] = seed_random

    print(json.dumps(prompt, indent=2))

    ws = websocket.WebSocket()
    print(f"Connecting to WebSocket: ws://{server_address}/ws?clientId={client_id}")
    ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
    print("WebSocket connected")

    print("Starting image generation...")
    images = get_images(ws, prompt)

    print("Saving generated images...")
    current_directory = os.getcwd()
    print(f"Current working directory: {current_directory}")

    for node_id in images:
        for i, image_data in enumerate(images[node_id]):
            image = Image.open(io.BytesIO(image_data))
            sanitized_filename = image_name.replace(" ", "_")
            filename = f"{sanitized_filename}_{i}.png"
            full_path = os.path.join(current_directory, filename)
            image.save(full_path)
            print(f"Saved image: {full_path}")

    print("Script execution completed")
    print(f"All images have been saved in the directory: {current_directory}")
    print("List of generated files:")
    for file in os.listdir(current_directory):
        if file.startswith(sanitized_filename):
            print(f" - {file}")


# ------------------------------------
choncum_list = [

    "only 1 people: He is looking for opportunities to learn new things.",
    "only 1 people: She is looking for good benefit packages.",
    "only 1 people: She is looking for opportunities to develop himself.",
    "only 1 people: He can get to the beach by going straight.",
    "only 1 people: She can get to the beach by going left.",
    "only 1 people: She can get to the beach by going along this road.",
    "only 1 people: She can walk there.",
    "only 1 people: She can get there by bike.",
    "only 1 people: He can get there by car.",
    "only 1 people: He can buy swimsuits at the store.",
    "only 1 people: He can buy swimsuits at the beach.",
    "only 1 people: She can buy swimsuits at the supermarket.",
    "only 1 people: He sells souvenirs on the beach.",
    "only 1 people: She sells souvenirs on the road.",
    "only 1 people: He sells souvenirs in the hotel.",
    "only 1 people: The dog is not allowed on the beach.",
    "only 1 people: The knife is not allowed on the beach.",
    "only 1 people: The bread is not allowed on the beach."
]

for user_input in choncum_list:
    try: # nếu bug thì ko bị dừng vòng lặp
        print(user_input)
        part_prompt = gen_prompt_image(user_input)
        full_prompt = f"commercial illustration, flat illustration, animation still, corporate animation style, wikihow illustration, quality illustration, 2d animation, 2 d animation, professional illustration, cartoon still, digital 2d animation, cg animation, animated still, illustrations, cartoon illustration, high quality, color block, 4k, simple detail, simple background, (flat illustration:1.2), no lines, (vector illustration:1.3), adobe illustration, {part_prompt}, (simple color:1.4), (flat style:1.4),(flat illustration style:1.4), <lora:Flat_Corporate_Style:1>, <lora:Fresh Ideas@pixar style_SDXL.safetensors:0.7>, <lora:Flat style:1.4> Flat style "
        print(full_prompt)
        print(user_input[15:])
        generate_images(image_name=user_input[15:], full_prompt=full_prompt)
    except Exception as e:
        print(f"Error occurred for user input '{user_input}': {e}")