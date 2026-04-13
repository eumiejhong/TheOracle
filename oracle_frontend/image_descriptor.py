import base64
import io
from PIL import Image as PILImage
import json
from oracle_frontend.ai_config import get_openai_client, OPENAI_MODEL

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


def describe_image_with_gpt4v(image_file, item_name_hint=None):
    image_bytes = image_file.read()
    try:
        img = PILImage.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        image_bytes = buf.getvalue()
    except Exception:
        pass
    image_data = base64.b64encode(image_bytes).decode("utf-8")

    hint_text = f"\nThe user says this item is: {item_name_hint}." if item_name_hint else ""

    prompt = f"""
    You are a fashion-aware visual assistant.

    Given the image provided, describe the item. Respond ONLY in structured JSON format, no commentary.

    Describe:
    1. Primary colors (e.g., navy, camel, burgundy)
    2. Any visible patterns (e.g., floral, checkered, striped, plain)
    3. The silhouette or structure (e.g., fitted, boxy, draped, cinched)
    4. The item type if visually inferable (e.g., sneakers, trousers, scarf)

    {hint_text}

    Format:
    {{
    "name_hint": "{item_name_hint}",
    "category_guess": "...",
    "colors": [...],
    "patterns": [...],
    "silhouette": "..."
    }}
        """

    response = get_openai_client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a structured visual fashion assistant."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ],
            },
        ],
        temperature=0.3,
    )

    try:
        content = response.choices[0].message.content
        json_start = content.find("{")
        json_end = content.rfind("}")
        parsed = json.loads(content[json_start:json_end+1])
        return parsed
    except Exception as e:
        return {"error": str(e)}


