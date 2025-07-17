#!/usr/bin/env python3
"""
AI Image Organizer - Web Interface
A Flask-based web interface for organizing AI-generated images with drag-and-drop,
real-time progress tracking, and visual gallery management.

Requirements:
- pip install flask pillow ollama sentence-transformers torch torchvision
- ollama pull qwen2.5vl
"""

import os
import json
import hashlib
import threading
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter
import shutil
import uuid

from flask import Flask, render_template, request, jsonify, send_from_directory
from PIL import Image
import ollama
from sentence_transformers import SentenceTransformer
import numpy as np

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Global state for tracking jobs
jobs = {}
job_lock = threading.Lock()

class ImageOrganizerWeb:
    def __init__(self):
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.jobs = {}
    
    def create_job(self, input_folder: str, output_folder: str, settings: dict) -> str:
        """Create a new organization job"""
        job_id = str(uuid.uuid4())
        
        job_data = {
            'id': job_id,
            'status': 'pending',
            'progress': 0,
            'total_images': 0,
            'processed_images': 0,
            'current_file': '',
            'input_folder': input_folder,
            'output_folder': output_folder,
            'settings': settings,
            'start_time': time.time(),
            'results': {},
            'error': None
        }
        
        with job_lock:
            jobs[job_id] = job_data
        
        # Start processing in background thread
        thread = threading.Thread(target=self._process_job, args=(job_id,))
        thread.daemon = True
        thread.start()
        
        return job_id
    
    def _process_job(self, job_id: str):
        """Process a job in the background"""
        try:
            with job_lock:
                job = jobs[job_id]
                job['status'] = 'running'
            
            # Find all images
            input_path = Path(job['input_folder'])
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
            image_files = []
            
            for ext in image_extensions:
                image_files.extend(input_path.glob(f"**/*{ext}"))
                image_files.extend(input_path.glob(f"**/*{ext.upper()}"))
            
            with job_lock:
                jobs[job_id]['total_images'] = len(image_files)
            
            if not image_files:
                with job_lock:
                    jobs[job_id]['status'] = 'error'
                    jobs[job_id]['error'] = 'No images found in the specified folder'
                return
            
            # Process images
            processed_images = []
            embeddings = {}
            
            for i, image_path in enumerate(image_files):
                try:
                    with job_lock:
                        jobs[job_id]['current_file'] = image_path.name
                        jobs[job_id]['processed_images'] = i
                        jobs[job_id]['progress'] = (i / len(image_files)) * 50  # First 50% is description
                    
                    # Verify image and get description
                    with Image.open(image_path) as img:
                        width, height = img.size
                    
                    description = self._describe_image(str(image_path), job['settings']['model'])
                    new_filename = self._generate_filename(description, str(image_path))
                    
                    image_info = {
                        'original_path': str(image_path),
                        'original_name': image_path.name,
                        'description': description,
                        'new_filename': new_filename,
                        'dimensions': (width, height),
                        'size_bytes': image_path.stat().st_size
                    }
                    
                    processed_images.append(image_info)
                    
                except Exception as e:
                    print(f"Error processing {image_path}: {e}")
                    continue
            
            # Group similar images
            with job_lock:
                jobs[job_id]['current_file'] = 'Grouping similar images...'
                jobs[job_id]['progress'] = 50
            
            groups = self._group_similar_images(
                processed_images, 
                job['settings']['similarity_threshold'],
                job['settings']['min_group_size']
            )
            
            # Organize files
            with job_lock:
                jobs[job_id]['current_file'] = 'Organizing files...'
                jobs[job_id]['progress'] = 75
            
            self._organize_files(
                groups, 
                job['output_folder'], 
                job['settings']['copy_files']
            )
            
            # Save results
            results = {
                'total_images': len(processed_images),
                'groups_created': len(groups),
                'groups': {name: len(images) for name, images in groups.items()}
            }
            
            with job_lock:
                jobs[job_id]['status'] = 'completed'
                jobs[job_id]['progress'] = 100
                jobs[job_id]['results'] = results
                jobs[job_id]['current_file'] = 'Complete!'
            
        except Exception as e:
            with job_lock:
                jobs[job_id]['status'] = 'error'
                jobs[job_id]['error'] = str(e)
    
    def _describe_image(self, image_path: str, model: str) -> str:
        """Generate description using Ollama"""
        try:
            prompt = """Analyze this image and provide a concise 5-8 word description focusing on:
1. Main subject (person, object, scene)
2. Art style (realistic, anime, abstract, fantasy, etc.)
3. Key visual elements (colors, mood, setting)

Format: [subject] [style] [key_elements]
Examples:
- "woman cyberpunk neon purple hair portrait"
- "dragon fantasy mountain castle sunset scene"  
- "abstract geometric colorful swirl pattern"
- "anime girl school uniform pink hair"

Description:"""
            
            response = ollama.generate(
                model=model,
                prompt=prompt,
                images=[image_path]
            )
            
            description = response['response'].strip()
            description = description.lower().replace('"', '').replace("'", "")
            
            # Clean for filename
            import re
            description = re.sub(r'[^\w\s-]', '', description)
            description = re.sub(r'\s+', ' ', description)
            
            return description.strip()
            
        except Exception as e:
            print(f"Error describing {image_path}: {e}")
            return "unknown_image"
    
    def _generate_filename(self, description: str, original_path: str) -> str:
        """Generate clean filename from description"""
        ext = Path(original_path).suffix.lower()
        filename = description.replace(' ', '_')
        
        import re
        filename = re.sub(r'[^\w\-_]', '', filename)
        filename = re.sub(r'_+', '_', filename)
        
        if len(filename) > 100:
            filename = filename[:100]
        
        filename = filename.rstrip('_')
        return f"{filename}{ext}"
    
    def _group_similar_images(self, images: List[Dict], threshold: float, min_group_size: int) -> Dict[str, List[Dict]]:
        """Group images by similarity"""
        # Compute embeddings
        descriptions = [img['description'] for img in images]
        embeddings = self.embedder.encode(descriptions)
        
        # Find groups
        groups = []
        used = set()
        
        for i, img in enumerate(images):
            if i in used:
                continue
                
            current_group = [img]
            used.add(i)
            
            # Find similar images
            for j, other_img in enumerate(images):
                if j in used:
                    continue
                    
                similarity = np.dot(embeddings[i], embeddings[j]) / (
                    np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
                )
                
                if similarity >= threshold:
                    current_group.append(other_img)
                    used.add(j)
            
            groups.append(current_group)
        
        # Organize into named groups
        organized_groups = {}
        catch_all = []
        
        for group in groups:
            if len(group) >= min_group_size:
                # Create group name from common words
                all_words = []
                for img in group:
                    all_words.extend(img['description'].split())
                
                word_counts = Counter(all_words)
                common_words = [word for word, count in word_counts.most_common(3)]
                group_name = '_'.join(common_words)
                
                # Ensure unique name
                counter = 1
                original_name = group_name
                while group_name in organized_groups:
                    group_name = f"{original_name}_{counter}"
                    counter += 1
                
                organized_groups[group_name] = group
            else:
                catch_all.extend(group)
        
        if catch_all:
            organized_groups['misc_singles'] = catch_all
        
        return organized_groups
    
    def _organize_files(self, groups: Dict[str, List[Dict]], output_folder: str, copy_files: bool):
        """Organize files into folders"""
        output_path = Path(output_folder)
        output_path.mkdir(exist_ok=True)
        
        for group_name, images in groups.items():
            group_folder = output_path / group_name
            group_folder.mkdir(exist_ok=True)
            
            if len(images) > 1:
                # Sequential naming for similar images
                images.sort(key=lambda x: x['original_name'])
                base_desc = images[0]['description']
                base_words = base_desc.split()[:4]
                base_name = '_'.join(base_words)
                
                for i, img in enumerate(images, 1):
                    ext = Path(img['original_path']).suffix
                    new_filename = f"{base_name}_{i:02d}{ext}"
                    
                    source = Path(img['original_path'])
                    dest = group_folder / new_filename
                    
                    if copy_files:
                        shutil.copy2(source, dest)
                    else:
                        shutil.move(str(source), dest)
            else:
                # Single image
                img = images[0]
                source = Path(img['original_path'])
                dest = group_folder / img['new_filename']
                
                if copy_files:
                    shutil.copy2(source, dest)
                else:
                    shutil.move(str(source), dest)

# Initialize organizer
organizer = ImageOrganizerWeb()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/start_job', methods=['POST'])
def start_job():
    """Start a new organization job"""
    data = request.json
    
    input_folder = data.get('input_folder')
    output_folder = data.get('output_folder')
    settings = data.get('settings', {})
    
    # Validate inputs
    if not input_folder or not output_folder:
        return jsonify({'error': 'Input and output folders are required'}), 400
    
    if not os.path.exists(input_folder):
        return jsonify({'error': 'Input folder does not exist'}), 400
    
    # Set default settings
    default_settings = {
        'model': 'qwen2.5vl',
        'similarity_threshold': 0.85,
        'min_group_size': 3,
        'copy_files': True
    }
    default_settings.update(settings)
    
    # Create job
    job_id = organizer.create_job(input_folder, output_folder, default_settings)
    
    return jsonify({'job_id': job_id})

@app.route('/api/job_status/<job_id>')
def job_status(job_id):
    """Get job status"""
    with job_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify(job)

@app.route('/api/jobs')
def list_jobs():
    """List all jobs"""
    with job_lock:
        return jsonify(list(jobs.values()))

@app.route('/api/browse_folder')
def browse_folder():
    """Browse folders for selection"""
    path = request.args.get('path', os.path.expanduser('~'))
    
    try:
        items = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                items.append({
                    'name': item,
                    'path': item_path,
                    'type': 'folder'
                })
        
        items.sort(key=lambda x: x['name'].lower())
        
        return jsonify({
            'current_path': path,
            'parent_path': os.path.dirname(path) if path != os.path.dirname(path) else None,
            'items': items
        })
    
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create the HTML template
    html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Image Organizer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }

        .header p {
            opacity: 0.9;
            font-size: 1.1rem;
        }

        .main-content {
            padding: 40px;
        }

        .setup-section {
            margin-bottom: 40px;
        }

        .section-title {
            font-size: 1.5rem;
            margin-bottom: 20px;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }

        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
        }

        .form-group label {
            margin-bottom: 8px;
            font-weight: 600;
            color: #555;
        }

        .form-group input,
        .form-group select {
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.3s;
        }

        .form-group input:focus,
        .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }

        .folder-selector {
            display: flex;
            gap: 10px;
            align-items: end;
        }

        .folder-selector input {
            flex: 1;
        }

        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
        }

        .btn-secondary {
            background: #f8f9fa;
            color: #555;
            border: 2px solid #e0e0e0;
        }

        .btn-secondary:hover {
            background: #e9ecef;
        }

        .settings-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .progress-section {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 30px;
            margin-top: 30px;
            display: none;
        }

        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 20px;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
            width: 0%;
        }

        .progress-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }

        .progress-stat {
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 8px;
        }

        .progress-stat .number {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }

        .progress-stat .label {
            color: #666;
            font-size: 0.9rem;
        }

        .current-file {
            background: white;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            margin-top: 20px;
        }

        .results-section {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 30px;
            margin-top: 30px;
            display: none;
        }

        .results-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .result-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }

        .result-card .number {
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
        }

        .error-message {
            background: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #c33;
            margin-top: 20px;
        }

        @media (max-width: 768px) {
            .form-grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .main-content {
                padding: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 AI Image Organizer</h1>
            <p>Transform your chaotic image collection into an organized masterpiece</p>
        </div>

        <div class="main-content">
            <div class="setup-section">
                <h2 class="section-title">📁 Folder Setup</h2>
                <div class="form-grid">
                    <div class="form-group">
                        <label for="inputFolder">Input Folder (Images to organize)</label>
                        <div class="folder-selector">
                            <input type="text" id="inputFolder" placeholder="Select folder containing your images...">
                            <button class="btn btn-secondary" onclick="browseFolder('input')">Browse</button>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="outputFolder">Output Folder (Where to save organized images)</label>
                        <div class="folder-selector">
                            <input type="text" id="outputFolder" placeholder="Select output folder...">
                            <button class="btn btn-secondary" onclick="browseFolder('output')">Browse</button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="setup-section">
                <h2 class="section-title">⚙️ Settings</h2>
                <div class="settings-grid">
                    <div class="form-group">
                        <label for="model">AI Model</label>
                        <select id="model">
                            <option value="qwen2.5vl">Qwen 2.5 VL (Recommended)</option>
                            <option value="llama3.2-vision">Llama 3.2 Vision</option>
                            <option value="granite3.2-vision">Granite 3.2 Vision</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="similarity">Similarity Threshold (0.7 = more groups, 0.9 = fewer groups)</label>
                        <input type="range" id="similarity" min="0.7" max="0.95" step="0.05" value="0.85">
                        <span id="similarityValue">0.85</span>
                    </div>
                    <div class="form-group">
                        <label for="minGroup">Minimum Group Size</label>
                        <input type="number" id="minGroup" min="2" max="10" value="3">
                    </div>
                    <div class="form-group">
                        <label for="copyFiles">File Operation</label>
                        <select id="copyFiles">
                            <option value="true">Copy files (safer, keeps originals)</option>
                            <option value="false">Move files (faster, saves space)</option>
                        </select>
                    </div>
                </div>
            </div>

            <div style="text-align: center;">
                <button class="btn btn-primary" onclick="startOrganization()" style="font-size: 1.2rem; padding: 15px 40px;">
                    🚀 Start Organization
                </button>
            </div>

            <div class="progress-section" id="progressSection">
                <h2 class="section-title">📊 Progress</h2>
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <div class="progress-info">
                    <div class="progress-stat">
                        <div class="number" id="progressPercent">0%</div>
                        <div class="label">Complete</div>
                    </div>
                    <div class="progress-stat">
                        <div class="number" id="processedCount">0</div>
                        <div class="label">Images Processed</div>
                    </div>
                    <div class="progress-stat">
                        <div class="number" id="totalCount">0</div>
                        <div class="label">Total Images</div>
                    </div>
                    <div class="progress-stat">
                        <div class="number" id="statusText">Starting...</div>
                        <div class="label">Status</div>
                    </div>
                </div>
                <div class="current-file" id="currentFile">
                    <strong>Current:</strong> <span id="currentFileName">Initializing...</span>
                </div>
            </div>

            <div class="results-section" id="resultsSection">
                <h2 class="section-title">✅ Results</h2>
                <div class="results-grid" id="resultsGrid">
                    <!-- Results will be populated here -->
                </div>
            </div>

            <div class="error-message" id="errorMessage" style="display: none;">
                <!-- Error messages will appear here -->
            </div>
        </div>
    </div>

    <script>
        let currentJobId = null;
        let progressInterval = null;

        // Update similarity display
        document.getElementById('similarity').addEventListener('input', function() {
            document.getElementById('similarityValue').textContent = this.value;
        });

        function browseFolder(type) {
            // For now, this is a placeholder - in a real implementation,
            // you'd want to use a proper file dialog or folder picker
            const input = document.getElementById(type + 'Folder');
            const folder = prompt(`Enter the path to your ${type} folder:`);
            if (folder) {
                input.value = folder;
            }
        }

        function startOrganization() {
            const inputFolder = document.getElementById('inputFolder').value;
            const outputFolder = document.getElementById('outputFolder').value;
            
            if (!inputFolder || !outputFolder) {
                alert('Please select both input and output folders');
                return;
            }

            const settings = {
                model: document.getElementById('model').value,
                similarity_threshold: parseFloat(document.getElementById('similarity').value),
                min_group_size: parseInt(document.getElementById('minGroup').value),
                copy_files: document.getElementById('copyFiles').value === 'true'
            };

            // Hide error message
            document.getElementById('errorMessage').style.display = 'none';
            
            // Show progress section
            document.getElementById('progressSection').style.display = 'block';
            document.getElementById('resultsSection').style.display = 'none';

            // Start the job
            fetch('/api/start_job', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    input_folder: inputFolder,
                    output_folder: outputFolder,
                    settings: settings
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showError(data.error);
                } else {
                    currentJobId = data.job_id;
                    startProgressTracking();
                }
            })
            .catch(error => {
                showError('Failed to start organization: ' + error);
            });
        }

        function startProgressTracking() {
            progressInterval = setInterval(updateProgress, 1000);
        }

        function updateProgress() {
            if (!currentJobId) return;

            fetch(`/api/job_status/${currentJobId}`)
            .then(response => response.json())
            .then(job => {
                updateProgressDisplay(job);
                
                if (job.status === 'completed') {
                    clearInterval(progressInterval);
                    showResults(job.results);
                } else if (job.status === 'error') {
                    clearInterval(progressInterval);
                    showError(job.error);
                }
            })
            .catch(error => {
                console.error('Error updating progress:', error);
            });
        }

        function updateProgressDisplay(job) {
            const progressFill = document.getElementById('progressFill');
            const progressPercent = document.getElementById('progressPercent');
            const processedCount = document.getElementById('processedCount');
            const totalCount = document.getElementById('totalCount');
            const statusText = document.getElementById('statusText');
            const currentFileName = document.getElementById('currentFileName');

            progressFill.style.width = job.progress + '%';
            progressPercent.textContent = Math.round(job.progress) + '%';
            processedCount.textContent = job.processed_images;
            totalCount.textContent = job.total_images;
            statusText.textContent = job.status.charAt(0).toUpperCase() + job.status.slice(1);
            currentFileName.textContent = job.current_file || 'Processing...';
        }

        function showResults(results) {
            const resultsSection = document.getElementById('resultsSection');
            const resultsGrid = document.getElementById('resultsGrid');
            
            resultsGrid.innerHTML = `
                <div class="result-card">
                    <div class="number">${results.total_images}</div>
                    <div class="label">Images Organized</div>
                </div>
                <div class="result-card">
                    <div class="number">${results.groups_created}</div>
                    <div class="label">Folders Created</div>
                </div>
                <div class="result-card">
                    <div class="number">${Math.round((results.total_images / results.groups_created) * 10) / 10}</div>
                    <div class="label">Avg Images per Folder</div>
                </div>
                <div class="result-card">
                    <div class="number">✅</div>
                    <div class="label">Organization Complete!</div>
                </div>
            `;
            
            resultsSection.style.display = 'block';
        }

        function showError(message) {
            const errorDiv = document.getElementById('errorMessage');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }
    </script>
</body>
</html>'''
    
    # Save the template
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print("🎨 AI Image Organizer Web Interface")
    print("=" * 50)
    print("✅ Starting web server...")
    print("✅ Navigate to: http://localhost:5000")
    print("✅ Make sure you have:")
    print("   - ollama running")
    print("   - qwen2.5vl model downloaded")
    print("   - Required Python packages installed")
    print("\n🚀 Ready to organize your 40K images!")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
