import os
import shutil
from moviepy import VideoFileClip

# 1. FIXED IMPORTS: Matching your actual file/function names
from step1_multi_cut import multi_segment_cut
from step2_stem_separation import separate_stems
from step3_final_sync_engine import process_voice_and_metadata 
from step4_final_vertical_reel import assemble_perfect_sync_reel

# CONFIGURATION FOR LOCAL TEST
RAW_VIDEO = "clips/raw.mp4"
# Using a 15-second range for a solid test
TEST_RANGES = [(10.0, 25.0)] 

def run_local_test(v_lang="hi-IN", s_lang="hi", gender="male"):
    print("🚀 STARTING LOCAL TERMINAL TEST")
    
    # 0. Clean old temporary outputs to prevent drift
    # We remove these folders entirely to ensure fresh AI translation
    for folder in ['stems', 'regional_outputs']:
        if os.path.exists(folder):
            print(f"🧹 Clearing {folder}...")
            shutil.rmtree(folder)
        os.makedirs(folder)

    # 1. Merge Video
    print("✂️ Cutting and Merging...")
    m_path = multi_segment_cut(RAW_VIDEO, TEST_RANGES) 
    if not m_path:
        print("❌ Error: Multi-cut failed to produce a file.")
        return

    # 2. Split Vocals/Music
    print("🎙️ AI Stem Separation...")
    separate_stems(m_path)

    # 3. Generate Synced Voice & Metadata
    # This step now forces English-to-Hindi translation
    print("🗣️ AI Translation & Sync...")
    process_voice_and_metadata("stems/only_vocals.wav", voice_lang=v_lang, sub_lang=s_lang, gender=gender)

    # 4. Assemble Final Vertical Reel
    # sub_pos=250 places text in the top black header
    print("✨ Burning Stylized Subtitles...")
    assemble_perfect_sync_reel(
        video_path=m_path,
        voice_path="regional_outputs/voice_sync.mp3",
        music_path="stems/only_music.wav",
        json_path="regional_outputs/metadata.json",
        sub_pos=250 
    )

    # 5. FINAL DURATION VALIDATION
    final_file = "final_reels/Master_Reel.mp4"
    if os.path.exists(final_file):
        with VideoFileClip(final_file) as check:
            print(f"✅ SUCCESS! Final Reel Duration: {check.duration:.2f} seconds.")
            if check.duration <= 1.0:
                print("⚠️ WARNING: The video is too short. Check MoviePy duration logic.")
    else:
        print("❌ Error: Final Reel was never created.")

if __name__ == "__main__":
    run_local_test()