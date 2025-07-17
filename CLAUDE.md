# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the AI Image Organizer project.

## Project Overview

AI Image Organizer is a Flask-based web application that uses AI vision models to automatically organize and categorize image collections. It leverages Ollama for local AI model serving and provides a clean web interface for managing large image libraries.

## Architecture

### Core Components

- **app.py**: Main Flask application with embedded HTML template
- **ImageOrganizerWeb class**: Core logic for image processing and organization
- **Web Interface**: Embedded HTML/CSS/JavaScript for user interaction
- **Background Processing**: Threading-based job management for non-blocking operations

### Key Technologies

- **Backend**: Flask (Python web framework)
- **AI Models**: Ollama (qwen2.5vl, llama3.2-vision, granite3.2-vision)
- **Embeddings**: SentenceTransformers (all-MiniLM-L6-v2)
- **Image Processing**: Pillow (PIL)
- **Frontend**: Vanilla HTML/CSS/JavaScript with responsive design

## Commands

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install and start Ollama
ollama serve
ollama pull qwen2.5vl

# Run application
python app.py
```

### Testing & Validation

```bash
# Test with sample images
mkdir test_input test_output
# Add some images to test_input/
python app.py  # Then use web interface

# Check requirements
pip check
python -c "import ollama; print('Ollama available')"

# Validate image processing
python -c "from PIL import Image; print('Pillow working')"
```

### Production Deployment

```bash
# Production server (use gunicorn)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Docker deployment
docker build -t ai-image-organizer .
docker run -p 5000:5000 ai-image-organizer
```

## Development Patterns

### Flask Application Structure

```python
# Single-file Flask app with embedded template
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Global state management
jobs = {}
job_lock = threading.Lock()

# RESTful API endpoints
@app.route('/api/start_job', methods=['POST'])
@app.route('/api/job_status/<job_id>')
@app.route('/api/jobs')
```

### Background Job Processing

- **Threading**: Uses `threading.Thread` for non-blocking background processing
- **Job State**: Global `jobs` dictionary with thread-safe locking
- **Progress Tracking**: Real-time progress updates via API polling
- **Error Handling**: Comprehensive exception handling with user feedback

### AI Integration Pattern

```python
# Ollama vision model integration
response = ollama.generate(
    model=model,
    prompt=prompt,
    images=[image_path]
)

# SentenceTransformers for similarity
embeddings = self.embedder.encode(descriptions)
similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
```

### File Organization Logic

1. **Discovery**: Recursive scan for image files
2. **Analysis**: AI-powered description generation
3. **Embedding**: Convert descriptions to numerical vectors
4. **Grouping**: Cluster similar images using cosine similarity
5. **Naming**: Generate folder names from common keywords
6. **Organization**: Copy/move files to structured folders

## Configuration

### Supported Models

- **qwen2.5vl** (recommended): Best overall accuracy
- **llama3.2-vision**: Good balance of speed/accuracy  
- **granite3.2-vision**: IBM model, good for technical images

### Default Settings

```python
default_settings = {
    'model': 'qwen2.5vl',
    'similarity_threshold': 0.85,
    'min_group_size': 3,
    'copy_files': True
}
```

### Supported Image Formats

```python
image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
```

## API Endpoints

### POST /api/start_job
Start new organization job
```json
{
  "input_folder": "/path/to/images",
  "output_folder": "/path/to/output",
  "settings": {
    "model": "qwen2.5vl",
    "similarity_threshold": 0.85,
    "min_group_size": 3,
    "copy_files": true
  }
}
```

### GET /api/job_status/{job_id}
Get job progress and status
```json
{
  "id": "uuid",
  "status": "running|completed|error",
  "progress": 75,
  "total_images": 100,
  "processed_images": 75,
  "current_file": "image.jpg",
  "results": {...}
}
```

## Frontend Architecture

### Responsive Design
- **Mobile-first**: CSS Grid and Flexbox layouts
- **CSS Custom Properties**: Consistent color scheme
- **Progressive Enhancement**: Works without JavaScript for basic functionality

### Real-time Updates
```javascript
// Progress polling pattern
progressInterval = setInterval(updateProgress, 1000);

function updateProgress() {
    fetch(`/api/job_status/${currentJobId}`)
    .then(response => response.json())
    .then(job => updateProgressDisplay(job));
}
```

## Performance Considerations

### Memory Management
- Processes images one at a time to limit memory usage
- Uses threading for I/O-bound operations
- Embeddings computed in batches

### Scalability
- Background processing prevents UI blocking
- Job-based architecture allows multiple concurrent operations
- Progress tracking provides user feedback

### Error Resilience
- Individual image failures don't stop batch processing
- Comprehensive error reporting to user
- Graceful degradation for missing models

## Security Notes

- Input validation on folder paths
- No user file uploads (local folder selection)
- Safe filename generation (sanitized descriptions)
- Local AI models (no external API calls)

## Testing Strategy

### Unit Testing
```python
# Test core functionality
def test_describe_image():
def test_group_similar_images():
def test_generate_filename():
```

### Integration Testing
```python
# Test with real Ollama models
def test_full_workflow():
def test_api_endpoints():
```

### Performance Testing
```bash
# Test with large image sets
python -m pytest tests/test_performance.py
```

## Common Issues & Solutions

### Ollama Connection
```python
# Check if Ollama is running
try:
    ollama.list()
except:
    print("Start Ollama: ollama serve")
```

### Memory Issues
- Reduce batch size for large collections
- Use "move" instead of "copy" for disk space
- Process in smaller chunks

### Permission Errors
- Ensure read access to input folder
- Ensure write access to output folder
- Check file locks on Windows

## Future Enhancements

- Docker containerization
- Database storage for job history
- Advanced filtering options
- Duplicate image detection
- Custom model training
- Bulk folder processing
- API authentication
- Cloud storage integration

## Dependencies

### Core Requirements
- flask==3.0.0
- pillow==10.0.1
- ollama==0.3.3
- sentence-transformers==2.2.2
- torch==2.1.0
- torchvision==0.16.0
- numpy==1.24.3

### Development Tools
- pytest (testing)
- black (code formatting)
- flake8 (linting)
- gunicorn (production server)