# Deploy SNS Studio Website to Render

## Step-by-Step Deployment

### 1. Go to Render Dashboard
Visit: https://dashboard.render.com/

### 2. Create New Web Service
- Click **New +** → **Web Service**
- Choose **Deploy from a Git repository**

### 3. Connect GitHub
- Click **Connect account** under GitHub
- Authorize Render to access your GitHub account
- Select your repository: `SNS-Project`
- Click **Connect**

### 4. Configure Service
Fill in these details:

| Field | Value |
|-------|-------|
| **Name** | sns-studio |
| **Region** | Choose your region |
| **Branch** | main |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `streamlit run web_app.py --server.address=0.0.0.0 --server.port=$PORT` |
| **Plan** | Free (or paid if needed) |

### 5. Set Environment Variables
Click **Add Environment Variable** and add:

```
PYTHON_VERSION = 3.13.7
GEMINI_MODEL = gemini-2.0-flash
OPENAI_MODEL = gpt-4o-mini
GROQ_MODEL = llama-3.3-70b-versatile
```

Optional (if you have API keys):
```
GEMINI_API_KEY = your_key_here
OPENAI_API_KEY = your_key_here
GROQ_API_KEY = your_key_here
```

### 6. Deploy
- Click **Create Web Service**
- Render will automatically build and deploy
- Watch the deploy logs
- Your site will be live in 2-5 minutes!

---

## After Deployment

Your site will be live at:
```
https://sns-studio.onrender.com
```

(Render generates a unique URL based on your service name)

### Share the Link
Send users to your deployed website. They can upload audio and use effects online!

### Auto-Deploy on GitHub Push
- Any push to `main` branch will auto-deploy
- No manual deployment needed in the future

---

## What the Website Offers

✅ **Upload Audio Files**
- MP3, WAV, OGG support
- No installation needed

✅ **Apply Audio Effects**
- Echo/Reverb
- Robot/Distortion  
- Pitch shifting
- Noise reduction

✅ **AI Enhancements**
- Voice presets (Chipmunk, Deep, etc.)
- Download processed audio

✅ **Real-time Visualization**
- Waveform display
- Frequency spectrum

---

## Troubleshooting

### Build Failed?
Check these common issues:
- Missing dependencies in `requirements.txt`
- Incorrect Python version
- Memory limit exceeded (free plan has 512MB)

### Site too slow?
- Free plan has limited resources
- Upgrade to paid plan for better performance

### Environment Variables Not Working?
- Make sure keys are set in Render dashboard
- Restart the service after adding variables

---

## Cost
- **Free Plan**: 0.5 GB RAM, perfect for testing
- **Starter Plan**: 0.5 GB RAM, $7/month (recommended)
- No costs for deploy or storage

---

**Status**: Ready to Deploy  
**Repository**: https://github.com/Arpit-Jindal-01/SNS-Project
