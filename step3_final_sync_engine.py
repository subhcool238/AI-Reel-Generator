import os, json, requests, mlx_whisper, base64, librosa
from pydub import AudioSegment
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

load_dotenv() 
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

if not SARVAM_API_KEY:
    raise ValueError("❌ Error: SARVAM_API_KEY not found. Check your .env file.")

def process_voice_and_metadata(vocal_path, voice_lang="hi-IN", sub_lang="hi", gender="male"):
    if not os.path.exists('regional_outputs'): os.makedirs('regional_outputs')
    
    video_dur = int(librosa.get_duration(path=vocal_path) * 1000)
    final_vocal = AudioSegment.silent(duration=video_dur)
    
    print("🚀 Transcribing with local MLX-Whisper...")
    result = mlx_whisper.transcribe(vocal_path, path_or_hf_repo="mlx-community/whisper-medium-mlx")
    
    segments_data = []
    # FIX: Force source='en' to prevent drifting back to English
    v_translator = GoogleTranslator(source='en', target=voice_lang.split('-')[0])
    s_translator = GoogleTranslator(source='en', target=sub_lang)
    speaker = "hitesh" if gender == "male" else "manisha"

    for i, seg in enumerate(result['segments']):
        txt = seg['text'].strip()
        if not txt: continue
        
        v_text = v_translator.translate(txt)
        s_text = s_translator.translate(txt)
        
        payload = {"text": v_text, "target_language_code": voice_lang, "speaker": speaker, "model": "bulbul:v2"}
        headers = {"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"}
        
        res = requests.post("https://api.sarvam.ai/text-to-speech", json=payload, headers=headers)
        if res.status_code == 200:
            p = f"regional_outputs/t_{i}.mp3"
            with open(p, "wb") as f: f.write(base64.b64decode(res.json()["audios"][0]))
            
            chunk = AudioSegment.from_file(p)
            final_vocal = final_vocal.overlay(chunk, position=int(seg['start'] * 1000))
            
            # Prevent overlaps: if next chunk's start is too close, trim the end
            # Using actual duration of the generated speech block instead of arbitrarily extending
            chunk_dur_sec = len(chunk) / 1000.0
            
            segments_data.append({
                "start": max(0, seg['start']), 
                "end": seg['start'] + chunk_dur_sec,
                "translated_text": s_text 
            })
            os.remove(p)

    final_vocal.export(f"regional_outputs/voice_sync.mp3", format="mp3")
    with open("regional_outputs/metadata.json", "w", encoding="utf-8") as f:
        json.dump({"segments": segments_data}, f, indent=4)