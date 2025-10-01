import base64
import json
import re
from openai import OpenAI

client = OpenAI(api_key="lm-studio", base_url="http://127.0.0.1:1234/v1")

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# cleaning function you posted (slightly adapted)
def clean_pan_output(raw_text: str):
    match = re.search(r"\{.*\}", raw_text, flags=re.S)
    if not match:
        raise ValueError("No JSON object found in model output")
    raw_json = match.group(0)
    raw_json = raw_json.replace("\\N", "\\n")
    data = json.loads(raw_json)
    def norm(x): return x.strip() if isinstance(x, str) else x
    data = {k: norm(v) for k, v in data.items()}

    if "Name" in data and data["Name"]:
        lines = [ln.strip() for ln in data["Name"].splitlines() if ln.strip()]
        if lines:
            data["Name"] = lines[0]
            if len(lines) > 1:
                data["Father's Name"] = lines[1]

    if "PAN Number" in data and data["PAN Number"]:
        data["PAN Number"] = re.sub(r"\s+", "", data["PAN Number"]).upper()

    return data

def ask_lm_with_image(prompt_text, image_path):
    image_b64 = encode_image_to_base64(image_path)
    content = [
        {"type": "text", "text": prompt_text},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
    ]

    # add a system message instructing JSON-only output
    messages = [
        {"role": "system", "content": "You are a helpful OCR assistant. Return ONLY a valid JSON object with keys: name, father_name, date_of_birth, pan_number."},
        {"role": "user", "content": content}
    ]

    resp = client.chat.completions.create(
        model="internvl3_5-4b",   # ensure this model supports vision
        messages=messages,
        temperature=0.0,
        max_tokens=1000,
        stream=False
    )
    return resp.choices[0].message.content

if __name__ == "__main__":
    prompt = (
        "Extract the Name, Father's Name, Date Of Birth, and PAN Number from the image. "
        "Return ONLY a JSON object exactly in this format: "
        '{ "Name": "...", "Father\'s Name": "...", "Date Of Birth": "...", "PAN Number": "..." }'
    )
    try:
        raw = ask_lm_with_image(prompt, "/Users/saurabhsachingosavi/video-kyc/abc1.jpg")
        print("Raw model output:\n", raw)
        cleaned = clean_pan_output(raw)
        print("Cleaned output:\n", json.dumps(cleaned, indent=2, ensure_ascii=False))
    except Exception as e:
        print("Error:", e)
