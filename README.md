# 🎨 AI Image Organizer

Transform your chaotic AI-generated image collection into a beautifully organized, searchable library using local vision models.

## ✨ What It Does

**Before:** `IMG_1234.jpg`, `download (47).png`, `untitled_artwork_final_v3.webp`

**After:** 
```
📁 cyberpunk_woman_neon/
  ├── cyberpunk_woman_neon_01.jpg
  ├── cyberpunk_woman_neon_02.jpg
  └── cyberpunk_woman_neon_03.jpg
📁 fantasy_dragon_mountain/
  ├── fantasy_dragon_mountain_01.jpg
  └── fantasy_dragon_mountain_02.jpg
📁 abstract_colorful_swirl/
  ├── abstract_colorful_swirl_01.jpg
  ├── abstract_colorful_swirl_02.jpg
  └── abstract_colorful_swirl_03.jpg
```

## 🚀 Key Features

- **🏠 100% Local** - No API costs, no internet required after setup
- **🔓 Uncensored** - Works with any content, no prudish AI restrictions
- **📊 Massive Scale** - Built to handle large collections (thousands of images)
- **🎯 Smart Grouping** - Similar images automatically grouped and named sequentially
- **🌐 Web Interface** - Beautiful, responsive UI with real-time progress tracking
- **⚡ Multiple Models** - Support for qwen2.5vl, llama3.2-vision, and more
- **🛡️ Safe Testing** - Copy mode preserves originals while you experiment

## 📋 Requirements

### System Requirements
- **Ollama** installed and running
- **Python 3.8+**
- **8GB+ RAM** recommended for large collections
- **GPU** optional but recommended for faster processing

### Required Models
```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Download vision model (recommended)
ollama pull qwen2.5vl

# Alternative models
ollama pull llama3.2-vision
ollama pull granite3.2-vision
```

### Python Dependencies
```bash
pip install flask pillow ollama sentence-transformers torch torchvision
```

## 🔧 Installation

1. **Clone the repository:**
```bash
git clone https://github.com/Cavedragon13/ai-image-organizer.git
cd ai-image-organizer
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Ensure Ollama is running:**
```bash
ollama serve
```

## 🎮 Usage

### Web Interface (Recommended)

1. **Start the web server:**
```bash
python image_organizer_web.py
```

2. **Open your browser:** http://localhost:5000

3. **Configure settings:**
   - **Input folder:** Your messy image collection
   - **Output folder:** Where organized images will go
   - **Similarity threshold:** 0.7 = more groups, 0.9 = fewer groups
   - **Model:** qwen2.5vl (recommended)
   - **Operation:** Copy (safer) or Move (faster)

4. **Hit "Start Organization"** and watch the magic happen!

### Command Line Interface

```bash
# Basic usage
python image_organizer.py /path/to/messy/images /path/to/organized/output

# Advanced options
python image_organizer.py /path/to/images /path/to/output \
    --model qwen2.5vl \
    --similarity 0.8 \
    --min-group 5 \
    --copy
```

## ⚙️ Configuration Options

| Setting | Description | Default | Notes |
|---------|-------------|---------|--------|
| **Model** | Vision model to use | `qwen2.5vl` | Best balance of quality/uncensored |
| **Similarity** | Grouping threshold | `0.85` | Lower = more specific groups |
| **Min Group Size** | Minimum images for a themed folder | `3` | Smaller groups go to "misc_singles" |
| **Copy Mode** | Copy vs move files | `true` | Copy is safer for testing |

## 🎯 Perfect For

- **AI Artists** - Organize generated artwork by style, subject, theme
- **Content Creators** - Sort large collections of generated assets
- **Researchers** - Categorize experimental outputs
- **Anyone** with a chaotic Downloads folder full of AI images

## 🔍 How It Works

1. **📷 Image Analysis** - Local vision model describes each image
2. **🧠 Smart Grouping** - Similar descriptions get grouped together  
3. **📝 Intelligent Naming** - Descriptive filenames based on content
4. **📁 Folder Organization** - Themed folders with sequential numbering
5. **📊 Progress Tracking** - Real-time updates on processing status

## 🛠️ Troubleshooting

### Common Issues

**"Model not found" error:**
```bash
ollama pull qwen2.5vl
```

**"Permission denied" on folders:**
```bash
# Make sure you have read/write access to input and output folders
chmod 755 /path/to/folders
```

**Images not being described:**
- Check if Ollama is running: `ollama list`
- Try a different model: `--model llama3.2-vision`
- Verify image formats are supported (jpg, png, webp, etc.)

**Web interface won't start:**
```bash
# Check if port 5000 is available
lsof -i :5000

# Use different port if needed
python image_organizer_web.py --port 8080
```

## 🤝 Contributing

Found a bug? Have a feature request? Contributions welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin amazing-feature`
5. Open a Pull Request

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Ollama** - For making local LLM deployment simple
- **Qwen Team** - For the excellent qwen2.5vl vision model
- **Pliny the Liberator** - For jailbreaking techniques and uncensored AI advocacy
- **The AI Art Community** - For generating the content that needed organizing in the first place

---

**⭐ Star this repo if it helped organize your chaotic image collection!**

*Made with ❤️ by [Cavedragon](https://github.com/Cavedragon13) for fellow AI artists drowning in unorganized masterpieces.*