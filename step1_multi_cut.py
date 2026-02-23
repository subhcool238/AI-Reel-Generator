import os
from moviepy import VideoFileClip, concatenate_videoclips

def multi_segment_cut(input_path, time_ranges):
    if not os.path.exists('clips'): 
        os.makedirs('clips')
    
    with VideoFileClip(input_path) as video:
        segments = []
        for i, (start, end) in enumerate(time_ranges):
            # FIX: Skip segments that are too short to process
            if end - start > 0.1:
                segments.append(video.subclipped(start, end))
        
        if not segments:
            print("❌ Error: No valid segments were selected.")
            return None
        
        final_video = concatenate_videoclips(segments, method="compose")
        output_path = "clips/merged_base.mp4"
        final_video.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", 
            preset="ultrafast", 
            threads=4
        )
        return output_path