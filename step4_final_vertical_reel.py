import os, json
from moviepy import VideoFileClip, AudioFileClip, CompositeVideoClip, ColorClip, TextClip
from moviepy.audio.AudioClip import CompositeAudioClip
import moviepy.audio.fx as afx

def assemble_perfect_sync_reel(video_path, voice_path, music_path, json_path, 
                               sub_color='#FFFF00', font_size=75, sub_pos=1550, words_per_line=3):
    
    with VideoFileClip(video_path) as video:
        final_dur = video.duration
        
        # Start at exactly 0.0s to sync with original audio
        voice = AudioFileClip(voice_path).with_effects([afx.MultiplyVolume(1.8)])
        
        audio_layers = [voice]
        if music_path and os.path.exists(music_path):
            music = AudioFileClip(music_path).with_effects([afx.MultiplyVolume(0.15)]).with_duration(final_dur)
            audio_layers.append(music)
        
        # Combine all audio tracks
        final_audio = CompositeAudioClip(audio_layers).with_duration(final_dur)
        
        # 2. CANVAS & VIDEO: Center the video horizontally and vertically
        canvas = ColorClip(size=(1080, 1920), color=(0,0,0), duration=final_dur)
        video_centered = video.resized(width=1080).with_position(("center", "center"))

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        font = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"

        # 3. SUBTITLES: Position at the BOTTOM (defaulting to 1550)
        subtitle_clips = []
        for seg in data.get("segments", []):
            words = seg.get('translated_text', '').split()
            chunks = [" ".join(words[i:i+words_per_line]) for i in range(0, len(words), words_per_line)]
            dur_per_chunk = (seg['end'] - seg['start']) / len(chunks)

            for i, txt in enumerate(chunks):
                # Padding added to height to prevent Hindi matra clipping
                sub = TextClip(
                    text=txt, font=font, font_size=font_size, color=sub_color,
                    method='caption', size=(950, int(font_size * 2.5)), 
                    text_align='center', duration=max(0.1, dur_per_chunk - 0.05)
                ).with_start(seg['start'] + (i * dur_per_chunk)).with_position(("center", 1550))
                subtitle_clips.append(sub)

        # 4. FINAL ASSEMBLY: Attach mixed audio and export
        final_video = CompositeVideoClip([canvas, video_centered] + subtitle_clips)
        final_video = final_video.with_audio(final_audio).with_duration(final_dur)
        
        if not os.path.exists('final_reels'): os.makedirs('final_reels')
        
        final_video.write_videofile(
            "final_reels/Master_Reel.mp4", 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            preset="ultrafast"
        )