import os, subprocess
from moviepy import VideoFileClip

def separate_stems(video_path):
    if not os.path.exists('stems'):
        os.makedirs('stems')

    audio_temp = "stems/temp_full_audio.wav"
    with VideoFileClip(video_path) as video:
        video.audio.write_audiofile(audio_temp)

    import shutil
    demucs_bin = shutil.which("demucs")
    if not demucs_bin:
        demucs_bin = "/Users/viragverma/Documents/Shubhanshu/Long to Short Reel/VideoMaster_V2/venv/bin/demucs"
    
    # htdemucs is optimized for vocal separation on Mac Studio
    subprocess.run([demucs_bin, "--two-stems", "vocals", "-o", "stems", audio_temp])

    base_out = "stems/htdemucs/temp_full_audio"
    if os.path.exists(f"{base_out}/vocals.wav"):
        os.rename(f"{base_out}/vocals.wav", "stems/only_vocals.wav")
        os.rename(f"{base_out}/no_vocals.wav", "stems/only_music.wav")