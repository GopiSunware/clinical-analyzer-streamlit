# What Gets Deployed to EC2

## Files That ARE Deployed (Required):

### Core Python Files (~200 KB total):
```
smartbuild_spa_middleware.py    # Main Streamlit application
session_manager.py              # Session/run management
requirement_gatherer.py         # Requirements extraction
system_prompts.py              # AI prompts
session_state_manager.py       # State management
```

### Utils Directory (~100 KB):
```
utils/
├── session_logger.py           # Logging system
├── smartbuild_progress_monitor.py  # Progress tracking
├── claude_supervisor.py        # Supervisor system
├── tmux_manager.py            # Tmux session management
├── comprehensive_xml_cleaner.py    # XML cleanup
└── startup_banner.py         # UI banner
```

### Documentation & Configuration (~500 KB):
```
CLAUDE.md                      # Project guidelines and documentation
.tmux.conf                     # Tmux configuration
requirements.txt               # Python dependencies

.claude/                       # Agent prompts and configurations
├── agents/
│   └── aws-architect.md      # AWS architect agent prompt
└── [other agent files]

docs/                          # Documentation folder
├── how_to_generate_aws_arch.md
├── aws-architect-master-guide.md
├── REQUIREMENTS_FLOW.md
├── SPA_MIDDLEWARE_ARCHITECTURE.md
└── [other documentation files]
```

### Assets (~50 KB):
```
assets/
├── favicon.ico
├── sunware_logo.png
├── sunware_icon.png
└── [other image assets]
```

### Empty Directories (Created on EC2):
```
sessions/                      # User sessions (created empty)
logs/                         # Application logs
deleted/                      # Trash folder
backups/                      # Backup storage
```

**Total Size Deployed: ~1-2 MB** (including documentation and configuration)

## Files that are NOT Deployed:

### Development Files (Not Needed):
```
env_ccc/                      # 500+ MB - Python virtual environment
.git/                         # Git repository
*.pyc                         # Compiled Python files
__pycache__/                  # Python cache
```

### Documentation (Not Needed):
```
docs/                         # Documentation files
*.md                          # Markdown files
README.md                     # Repository readme
CLAUDE.md                     # Development guidelines
```

### Deployment Scripts (Stay Local):
```
deploy/                       # Deployment scripts
```

### Old/Test Files (Not Needed):
```
archive/                      # Old versions
backups/                      # Local backups
test_*.py                     # Test files
simple_json_extract.py       # Test utilities
websocket_server_fixed.py    # WebSocket tests
```

### Large Session Data (Not Needed):
```
sessions/session_*/           # Existing session data
deleted/                      # Deleted sessions
```

## Why This Separation?

1. **Security**: Don't expose development files, git history, or credentials
2. **Performance**: EC2 only needs runtime files (~400 KB vs 600+ MB)
3. **Cost**: Smaller deployment = faster uploads, less storage
4. **Clean Environment**: Production doesn't need test/development files

## Storage on EC2:

### After Deployment:
```
/opt/smartbuild/
├── smartbuild_spa_middleware.py
├── session_manager.py
├── requirement_gatherer.py
├── system_prompts.py
├── session_state_manager.py
├── CLAUDE.md                # Project documentation
├── .tmux.conf               # Tmux configuration
├── .claude/                 # Agent prompts directory
│   └── agents/
│       └── aws-architect.md
├── docs/                    # Documentation folder
│   ├── how_to_generate_aws_arch.md
│   ├── aws-architect-master-guide.md
│   └── [other docs]
├── utils/
│   └── [utility modules]
├── assets/                  # Logos and icons
│   └── [image files]
├── requirements.txt
├── venv/                    # Created on EC2
├── sessions/                # User sessions (includes existing data)
├── logs/                    # Empty, fills with logs
├── deleted/                 # Empty, fills with deletions
└── backups/                 # Empty, for backups
```

## Important Notes:

1. **Sessions are local to each EC2**: User sessions created on EC2 stay there
2. **No database needed**: Sessions stored as files locally
3. **No S3 needed**: Everything runs from local EC2 storage
4. **Virtual env created on EC2**: Python packages installed directly on server

## To Deploy:
```bash
# After running simple-deploy.sh, upload only necessary files:
./upload.sh <EC2_IP>
```

This uploads only ~400 KB instead of the entire 600+ MB folder!