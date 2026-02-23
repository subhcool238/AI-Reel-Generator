import os
import shutil
import uuid
import json
import threading
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
import yt_dlp

# Existing scripts
from step1_multi_cut import multi_segment_cut
from step2_stem_separation import separate_stems
from step3_final_sync_engine import process_voice_and_metadata 
from step4_final_vertical_reel import assemble_perfect_sync_reel

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

TASKS = {}

def process_pipeline(task_id, raw_video, time_ranges, voice_lang, sub_lang, gender):
    try:
        TASKS[task_id]['status'] = 'Processing'
        TASKS[task_id]['message'] = 'Initializing...'

        for folder in ['stems', 'regional_outputs', 'clips', 'final_reels']:
            if os.path.exists(folder):
                shutil.rmtree(folder, ignore_errors=True)
            os.makedirs(folder)

        TASKS[task_id]['message'] = 'Cutting and Merging video segments...'
        m_path = multi_segment_cut(raw_video, time_ranges)
        if not m_path:
            raise Exception("Multi-cut failed to produce a file.")

        TASKS[task_id]['message'] = 'Separating Stems (Vocals/Music)...'
        separate_stems(m_path)

        TASKS[task_id]['message'] = 'AI Translation & Syncing Voice...'
        process_voice_and_metadata("stems/only_vocals.wav", voice_lang=voice_lang, sub_lang=sub_lang, gender=gender)

        TASKS[task_id]['message'] = 'Assembling Final Vertical Reel...'
        assemble_perfect_sync_reel(
            video_path=m_path,
            voice_path="regional_outputs/voice_sync.mp3",
            music_path="stems/only_music.wav",
            json_path="regional_outputs/metadata.json",
            sub_pos=250 
        )

        final_file = "final_reels/Master_Reel.mp4"
        if os.path.exists(final_file):
            
            # Save final to task specific folder
            os.makedirs(f"outputs/{task_id}", exist_ok=True)
            final_output = f"outputs/{task_id}/Master_Reel.mp4"
            shutil.copy(final_file, final_output)
            
            TASKS[task_id]['status'] = 'Done'
            TASKS[task_id]['result_path'] = final_output
        else:
            raise Exception("Final Reel was never created.")

    except Exception as e:
        print(f"Error in task {task_id}: {str(e)}")
        TASKS[task_id]['status'] = 'Error'
        TASKS[task_id]['message'] = str(e)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    # Handle File Upload
    if 'file' in request.files and request.files['file'].filename != '':
        file = request.files['file']
        filename = secure_filename(file.filename)
        uid = str(uuid.uuid4())
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{uid}_{filename}")
        file.save(filepath)
        return jsonify({"success": True, "filepath": filepath})

    # Handle YouTube URL
    data = request.form
    youtube_url = data.get('youtube_url')
    if youtube_url:
        uid = str(uuid.uuid4())
        out_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{uid}_youtube.mp4")
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': out_path,
            'merge_output_format': 'mp4',
            'noplaylist': True,
        }
        try:
            print(f"Downloading YouTube URL: {youtube_url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
            print("Download completed:", out_path)
            return jsonify({"success": True, "filepath": out_path})
        except Exception as e:
            print("YT Download Failed:", str(e))
            return jsonify({"success": False, "error": str(e)})

    return jsonify({"success": False, "error": "No file or URL provided."})


@app.route('/process', methods=['POST'])
def process_vid():
    data = request.json
    filepath = data.get('filepath')
    ranges = data.get('ranges', [])
    voice_lang = data.get('voice_lang', 'hi-IN')
    sub_lang = data.get('sub_lang', 'hi')
    gender = data.get('gender', 'male')

    if not filepath or not os.path.exists(filepath):
        return jsonify({"success": False, "error": "Invalid filepath."})
    
    if not ranges:
        return jsonify({"success": False, "error": "No time ranges provided."})

    time_ranges = [(float(r['start']), float(r['end'])) for r in ranges]

    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        'status': 'Queued',
        'message': 'Queued...',
        'result_path': None
    }

    thread = threading.Thread(target=process_pipeline, args=(task_id, filepath, time_ranges, voice_lang, sub_lang, gender))
    thread.start()

    return jsonify({"success": True, "task_id": task_id})

@app.route('/status/<task_id>', methods=['GET'])
def status(task_id):
    if task_id not in TASKS:
        return jsonify({"error": "Invalid task ID"}), 404
    return jsonify(TASKS[task_id])

@app.route('/download/<task_id>', methods=['GET'])
def download(task_id):
    if task_id not in TASKS or TASKS[task_id]['status'] != 'Done':
        return "Not ready or invalid ID", 400
    file_path = TASKS[task_id]['result_path']
    # Change as_attachment to False so the browser can actually display the video in the <video> tag natively 
    return send_file(file_path, as_attachment=False, mimetype='video/mp4')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
