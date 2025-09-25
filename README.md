# 🏥 Clinical Document Analyzer

A comprehensive AI-powered clinical document analysis system that ingests medical records, images, and patient data to provide intelligent search and analysis capabilities for healthcare professionals.

## ✨ Features

- **Automatic Data Ingestion**: Processes Excel files, Word documents, images from the dataset folder
- **AI-Powered Image Transcription**: Uses Google Vision API to extract text from medical images  
- **Smart Patient Matching**: Groups data by patient using fuzzy matching for names and IDs
- **Natural Language Queries**: Ask questions about patients in plain English
- **Chat Interface**: Streamlit-based UI with sidebar statistics and patient context
- **Embedded Database**: SQLite for local storage with no external dependencies

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment
Copy `env_example.txt` to `.env` and configure:
```
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
```

### 3. Add Google Vision API Key
Place your Google Vision API key file as `key.json` in the root directory.

### 4. Run the Application  
```bash
streamlit run app.py
```

### Claude Sub-agent Mode (No External API Keys)

If you prefer to route questions through the locally authenticated Claude CLI instead of OpenAI/Gemini:

1. Install and authenticate the CLI once: `claude login`
2. Set `AI_PROVIDER=claude_subagent` in your environment (see `env_example.txt`)
3. Optional: override `CLAUDE_SUBAGENT_MODEL` if you need a different Claude sub-agent
4. Launch the app normally; responses will be generated via Claude sub-agents and persisted under `subagent_sessions/`

## 📁 Data Organization

The system is **completely flexible** with folder structure! Simply place your files anywhere within the `dataset` folder:

```
dataset/
├── Any_Folder_Name/
│   ├── patient_records.xlsx
│   ├── CT_Scans/
│   │   ├── scan1.jpg
│   │   └── scan2.jpg
│   └── Reports/
│       └── report.docx
├── Patient_Episodes/
├── Medical_Images/
└── ... (any structure you prefer)
```

**Supported File Types:**
- **Documents**: `.xlsx`, `.xls`, `.docx`, `.txt` 
- **Images**: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`

The system will automatically:
- 🔍 **Scan recursively** through all subfolders
- 📋 **Categorize files** by extension (not location)
- 🏷️ **Extract patient info** from filenames and folder names
- 🖼️ **Detect image categories** from folder names (CT, MRI, X-Ray, etc.)

## 🔍 Usage

1. **Automatic Ingestion**: The app automatically processes files on startup
2. **Patient Selection**: Use the sidebar to select a specific patient for focused queries
3. **Ask Questions**: Type natural language questions about patient data
4. **View Statistics**: Monitor ingestion progress and database stats in the sidebar

## 🛠️ Technical Details

- **Database**: SQLite with fuzzy patient matching
- **AI Models**: OpenAI GPT for text processing, Google Vision for images
- **Interface**: Streamlit with responsive design
- **File Processing**: Handles Excel, DOCX, TXT, and image formats

## 📊 Architecture

- `src/database_manager.py` - SQLite database operations
- `src/document_processor.py` - File parsing and AI processing  
- `src/ingestion_manager.py` - Orchestrates data processing
- `src/chat_assistant.py` - Natural language query handling
- `app.py` - Streamlit web interface

## 🔧 Configuration

Environment variables in `.env`:
- `OPENAI_API_KEY` - Required for text processing
- `OPENAI_MODEL` - GPT model (default: gpt-3.5-turbo)  
- `DATABASE_NAME` - SQLite file name
- `MAX_TOKENS` - AI response length limit
- `TEMPERATURE` - AI creativity level

## 🛠️ Troubleshooting

### "Client.init() got an unexpected keyword argument 'proxies'"

This error indicates an OpenAI library version compatibility issue. Run the fix script:

```bash
python fix_openai.py
```

Or manually fix:
```bash
pip install --upgrade openai>=1.12.0
```

### Other Common Issues

- **"OpenAI API key not found"** - Check your `.env` file has `OPENAI_API_KEY`
- **"Google Vision API not configured"** - Place `key.json` in root directory  
- **"No files to process"** - Ensure files exist in `/dataset` folder with supported extensions 

## 🚀 Quick Setup

### Prerequisites
- Python 3.8+
- OpenAI API Key
- Google Cloud Vision API Key (for medical image transcription)

### Installation
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables (see Configuration below)
4. Run: `streamlit run app.py`

## 🌐 Cloud Deployment Snapshot (2025-09-24)

The application is currently hosted on AWS behind CloudFront: **https://d1kmcm08kwn7a6.cloudfront.net**. The stack name is `clinical-analyzer-minimal` in `us-east-1`, and it provisions a `t3a.micro` EC2 instance (latest public IP: `18.206.218.43`) plus an IAM role with access to the artifacts bucket `s3://clinical-analyser-artifacts-057669459602`.

Deploy/update workflow:

```bash
# 1) Build the artifact bundle (excludes secrets)
mkdir -p dist
zip -r dist/clinical-analyser.zip . \
  -x 'dist/*' '.git/*' '*.pyc' '__pycache__/*' 'env' 'env/*' 'key.json' \
     'deploy/keys/*' 'git_commit/PRIVATE_GITHUB_PAT.txt'

# 2) Upload the bundle
aws s3 cp dist/clinical-analyser.zip \
  s3://clinical-analyser-artifacts-057669459602/artifacts/clinical-analyser.zip

# 3) Create/Update the CloudFormation stack
aws cloudformation deploy \
  --stack-name clinical-analyzer-minimal \
  --template-file deploy/infrastructure/clinical-analyzer-minimal.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    KeyPairName=smartbuild-20250824180036 \
    VpcId=vpc-0bc30631a28503c95 \
    PublicSubnetId=subnet-0bee8301325571ebf \
    ArtifactBucket=clinical-analyser-artifacts-057669459602 \
    ArtifactObjectKey=artifacts/clinical-analyser.zip \
    InstanceType=t3a.micro

# 4) Inspect current endpoints / IP
aws cloudformation describe-stacks \
  --stack-name clinical-analyzer-minimal \
  --query 'Stacks[0].Outputs'
```

After the stack converges, replace the dummy values in `/opt/clinical-analyzer/.env` on the EC2 host (`ssh -i smartbuild-20250824180036.pem ubuntu@18.206.218.43`) with live API keys and restart the `clinical-analyzer` service. To remove infra, delete the stack and purge the S3 object/bucket.

## ⚙️ Configuration

### 1. OpenAI API Setup
Create a `.env` file with:
```
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo  # or gpt-4 for better performance
DATABASE_NAME=clinical_analyzer.db
```

### 2. Google Vision API Setup (For Medical Image Analysis)

**Why needed:** The system uses Google Vision API to extract text from medical images (scans, reports, X-rays, etc.) and then analyzes them with AI.

**Steps:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the "Cloud Vision API"
4. Create a Service Account:
   - Go to IAM & Admin > Service Accounts
   - Click "Create Service Account"
   - Give it a name like "clinical-analyzer-vision"
   - Grant role: "Cloud Vision API Service Agent"
5. Generate and download the JSON key:
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key" > "JSON"
   - Download the JSON file
6. **Rename the downloaded file to `key.json`** and place it in your project root

**File structure should look like:**
```
clinical-analyser-poc/
├── app.py
├── key.json          ← Your Google Vision API key file
├── .env              ← Your OpenAI API key
├── requirements.txt
└── ...
```

### 3. Alternative: OpenAI Vision API (Option 2)
If you prefer to use OpenAI's GPT-4V instead of Google Vision, we can modify the code to use OpenAI's vision capabilities for medical image analysis.

## 🖼️ Medical Image Processing

The system processes medical images in two stages:
1. **Text Extraction:** Google Vision API extracts text from medical images
2. **AI Analysis:** OpenAI GPT analyzes the extracted text in context of patient records

**Supported formats:** JPEG, PNG, TIFF, BMP
**Medical image types:** X-rays, CT scans, MRI, ultrasounds, pathology reports, etc.

## 📊 Dataset Structure

The system expects medical data in Excel format with image references:
- **Patient Information:** Name, ID, demographics
- **Clinical Data:** Diagnoses, treatments, medical history  
- **Image Links:** References to medical images for each patient

## 🎯 Features

- **AI-Powered Chat:** Ask questions about patients, diagnoses, treatments
- **Medical Image Analysis:** Extract insights from X-rays, scans, reports
- **Patient Context:** Focus conversations on specific patients
- **Comprehensive Search:** Find patterns across all medical records
- **Dark Theme:** Optimized for medical professional workflow

## 🔧 Troubleshooting

### "No medical imaging results" error
- Check if `key.json` exists in project root
- Verify Google Cloud Vision API is enabled
- Check API quotas and billing in Google Cloud Console

### OpenAI API errors  
- Verify your OpenAI API key in `.env` file
- Check your OpenAI account has available credits
- Try switching to a different model (gpt-3.5-turbo vs gpt-4)

## 🚀 Usage

1. Start the application: `streamlit run app.py`
2. Upload your clinical dataset (Excel file)
3. Wait for image processing to complete
4. Select a patient or ask general questions
5. Get AI-powered insights from medical records and images

## 📝 Example Queries

- "What are David's scan results?"
- "Show me patients with heart conditions" 
- "What does the chest X-ray show?"
- "Analyze the imaging findings for patient M1283"

## 🔒 Privacy & Security

- All data is processed locally
- No patient data sent to external services beyond API calls
- Medical images analyzed with HIPAA-conscious practices
- Secure API key management through environment variables 
