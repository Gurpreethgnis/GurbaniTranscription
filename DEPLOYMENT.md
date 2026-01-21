# Shabad Guru - RunPod Deployment Guide

This guide explains how to deploy Shabad Guru to RunPod with GPU support, persistent storage, and secure authentication.

## Prerequisites

1. **RunPod Account**: Sign up at [runpod.io](https://runpod.io)
2. **Docker Hub Account** (optional): For hosting your own image
3. **SSH Client**: For accessing your pod

## Quick Start

### Option 1: Using RunPod Templates (Recommended)

1. **Create a Pod**:
   - Go to RunPod → Pods → Create Pod
   - Select GPU: **RTX 4090** or **A100** recommended (for `large-v3` model)
   - Minimum specs: 16GB VRAM, 16GB RAM, 50GB disk

2. **Choose Template**:
   - Select: **RunPod Pytorch 2.1** template
   - Or use a custom Docker image (see Option 2)

3. **Configure Environment**:
   Add these environment variables in the pod settings:
   ```
   FLASK_SECRET_KEY=<generate-a-32-char-random-string>
   ADMIN_EMAIL=your-admin@email.com
   ADMIN_PASSWORD=<your-secure-password>
   ```

4. **Start the Pod** and connect via SSH or Web Terminal

5. **Deploy the Application**:
   ```bash
   # Clone the repository
   git clone <your-repo-url> /workspace/shabad-guru
   cd /workspace/shabad-guru
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Start the application
   python app.py
   ```

### Option 2: Using Docker Image

1. **Build and Push Image** (from your local machine):
   ```bash
   # Build the image
   docker build -t your-username/shabad-guru:latest .
   
   # Push to Docker Hub
   docker push your-username/shabad-guru:latest
   ```

2. **Create RunPod Pod**:
   - Container Image: `your-username/shabad-guru:latest`
   - Expose Port: `5000`
   - Volume Mount: `/workspace` → `/app/data` (for persistence)

3. **Set Environment Variables**:
   ```
   FLASK_SECRET_KEY=<your-secret>
   ADMIN_EMAIL=admin@example.com
   ADMIN_PASSWORD=<secure-password>
   DATABASE_URL=sqlite:////workspace/shabad_guru.db
   ```

## Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `FLASK_SECRET_KEY` | **Yes** | Secret for session encryption | Random (insecure) |
| `ADMIN_EMAIL` | **Yes** | Initial admin email | `admin@shabadguru.local` |
| `ADMIN_PASSWORD` | **Yes** | Initial admin password | `changeme123` |
| `DATABASE_URL` | No | SQLite database path | `sqlite:///data/shabad_guru.db` |
| `WHISPER_MODEL_SIZE` | No | Whisper model to use | `large-v3` (GPU), `small` (CPU) |
| `ASR_PRIMARY_PROVIDER` | No | Primary ASR provider | `whisper` |

### Generate Secure Secret Key

```bash
# Python
python -c "import secrets; print(secrets.token_hex(32))"

# Or using openssl
openssl rand -hex 32
```

## Persistent Storage

RunPod provides `/workspace` as persistent storage. Mount volumes to preserve:

```yaml
volumes:
  # Database (user accounts, transcription history)
  - /workspace/data:/app/data
  
  # Uploads and outputs
  - /workspace/uploads:/app/uploads
  - /workspace/outputs:/app/outputs
  
  # Model cache (avoid re-downloading)
  - /workspace/.cache:/root/.cache
```

## Network Configuration

### Expose HTTP Port

In RunPod pod settings:
- HTTP Port: `5000`
- Enable "Expose HTTP Ports"

You'll get a URL like: `https://xxx-5000.proxy.runpod.net`

### Custom Domain (Optional)

1. Get your pod's public URL
2. Create a CNAME record pointing to it
3. Consider using Cloudflare for SSL and caching

## Security Best Practices

1. **Change Default Credentials**: Never use default admin password in production
2. **Use Strong Secret Key**: Generate a 32+ character random key
3. **Enable HTTPS**: RunPod provides HTTPS by default via their proxy
4. **Restrict Access**: Use invite-only registration (already configured)
5. **Regular Backups**: Back up `/workspace/data/shabad_guru.db` regularly

## GPU Selection Guide

| GPU | VRAM | Best For | Cost/hr (approx) |
|-----|------|----------|------------------|
| RTX 3090 | 24GB | Development, testing | $0.30-0.50 |
| RTX 4090 | 24GB | Production, fast processing | $0.50-0.80 |
| A100 40GB | 40GB | Heavy workloads, batch | $1.50-2.00 |
| A100 80GB | 80GB | Maximum performance | $2.00-3.00 |

For Whisper `large-v3` model:
- Minimum: RTX 3090 (24GB)
- Recommended: RTX 4090 or A100

## Monitoring & Maintenance

### View Logs

```bash
# SSH into pod
ssh root@<pod-ip>

# View application logs
tail -f /app/logs/transcription.log

# View container logs (if using Docker)
docker logs -f shabad-guru
```

### Health Check

```bash
curl http://localhost:5000/status
```

Expected response:
```json
{
  "status": "ok",
  "orchestrator_loaded": true,
  "model_size": "large-v3"
}
```

### Backup Database

```bash
# From inside pod
cp /workspace/data/shabad_guru.db /workspace/backups/shabad_guru_$(date +%Y%m%d).db

# Or download via RunPod file manager
```

## Troubleshooting

### Out of Memory

If you get CUDA OOM errors:
1. Use a smaller model: `WHISPER_MODEL_SIZE=medium`
2. Upgrade to a GPU with more VRAM
3. Reduce batch size in processing

### Slow Startup

First startup takes 5-10 minutes to:
1. Download Whisper models (~3GB for large-v3)
2. Initialize CUDA and transformers

Subsequent startups are faster with cached models.

### Connection Refused

1. Check pod is running: `docker ps`
2. Check application started: `curl localhost:5000/status`
3. Check RunPod HTTP port is exposed

### Permission Denied

```bash
# Fix volume permissions
chmod -R 755 /workspace/data /workspace/uploads /workspace/outputs
```

## Cost Optimization

1. **Spot Instances**: Use RunPod spot for 50-70% savings (with interruption risk)
2. **Auto-Stop**: Configure pod to stop when idle
3. **Smaller Model**: Use `medium` for lighter workloads
4. **Batch Processing**: Process files in batches during off-peak hours

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   RunPod Pod                         │
│  ┌───────────────────────────────────────────────┐  │
│  │              Docker Container                  │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │         Flask Application                │  │  │
│  │  │  • Authentication (Flask-Login)          │  │  │
│  │  │  • Transcription (Whisper/ASR)          │  │  │
│  │  │  • WebSocket (Live Mode)                │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  │                     │                          │  │
│  │  ┌─────────────────┴─────────────────────┐   │  │
│  │  │     SQLite DB     │    Model Cache     │   │  │
│  │  └───────────────────┴───────────────────┘   │  │
│  └───────────────────────────────────────────────┘  │
│                     │                                │
│  ┌─────────────────┴──────────────────────────────┐ │
│  │            /workspace (Persistent)              │ │
│  │  • data/shabad_guru.db                         │ │
│  │  • uploads/                                    │ │
│  │  • outputs/                                    │ │
│  │  • .cache/ (Whisper models)                    │ │
│  └─────────────────────────────────────────────────┘ │
│                     │                                │
│            ┌───────┴───────┐                        │
│            │  NVIDIA GPU   │                        │
│            │  (RTX 4090)   │                        │
│            └───────────────┘                        │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
              RunPod HTTP Proxy
         (https://xxx.proxy.runpod.net)
                      │
                      ▼
                   Users
```

## Support

For issues:
1. Check the logs in `/app/logs/transcription.log`
2. Review RunPod pod metrics
3. Contact RunPod support for infrastructure issues

