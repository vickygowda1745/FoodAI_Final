"""
===========================================================
FoodAI Utility Functions
===========================================================
"""

import io
import json
import base64
import time
from PIL import Image


############################################################
# TIMER
############################################################

class Timer:

    def __init__(self):

        self.start = time.time()

    def elapsed(self):

        return round(

            time.time() - self.start,

            2

        )


############################################################
# IMAGE
############################################################

def prepare_image(image_data):

    if "," in image_data:

        image_data = image_data.split(",",1)[1]

    raw = base64.b64decode(image_data)

    img = Image.open(

        io.BytesIO(raw)

    ).convert("RGB")

    w,h = img.size

    longest = max(w,h)

    if longest > 1024:

        scale = 1024/longest

        img = img.resize(

            (

                int(w*scale),

                int(h*scale)

            ),

            Image.Resampling.LANCZOS

        )

    out = io.BytesIO()

    img.save(

        out,

        "JPEG",

        quality=80,

        optimize=True

    )

    return base64.b64encode(

        out.getvalue()

    ).decode()


############################################################
# JSON
############################################################

def clean_json(text):

    text = text.strip()

    if text.startswith("```"):

        text = text.replace(

            "```json",

            ""

        )

        text = text.replace(

            "```",

            ""

        )

    return json.loads(text)


############################################################
# NUMBER
############################################################

def number(value,default=0):

    try:

        return float(value)

    except:

        return float(default)


############################################################
# CLAMP
############################################################

def clamp(v,a,b):

    return max(

        a,

        min(

            b,

            v

        )

    )