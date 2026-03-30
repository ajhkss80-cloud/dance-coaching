#!/usr/bin/env bash
# ==============================================================================
# Dance Coaching Platform - MimicMotion GPU Model Setup (Linux / WSL)
# ==============================================================================
# Downloads and configures MimicMotion for local GPU-based video generation.
# Requires: git, python3 with CUDA-capable PyTorch, ~15 GB disk space.
#
# Run from the repository root:
#     bash scripts/setup-mimicmotion.sh
# ==============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR_DIR="$ROOT_DIR/vendor"
MODELS_DIR="$ROOT_DIR/models"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC}    $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
fail() { echo -e "${RED}[FAIL]${NC}  $1"; }
info() { echo -e "${CYAN}[INFO]${NC}  $1"; }

echo ""
echo "====================================="
echo "  MimicMotion GPU Setup"
echo "====================================="
echo ""
echo -e "${YELLOW}WARNING: This will download approximately 15 GB of model weights.${NC}"
echo -e "${YELLOW}Make sure you have sufficient disk space and a stable connection.${NC}"
echo ""
read -p "Continue? [y/N] " -r
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi
echo ""

# ---------- check prerequisites ----------

# git
if ! command -v git &>/dev/null; then
    fail "git is required but not found"
    exit 1
fi

# Check for huggingface-cli or wget
HAS_HF_CLI=false
if command -v huggingface-cli &>/dev/null; then
    HAS_HF_CLI=true
    ok "huggingface-cli found"
elif command -v wget &>/dev/null; then
    ok "wget found (will use for downloads)"
else
    fail "Neither huggingface-cli nor wget found"
    echo "       Install huggingface-cli:  pip install huggingface_hub[cli]"
    echo "       Or install wget:          sudo apt install wget"
    exit 1
fi

# ---------- create directories ----------

info "Creating vendor/ and models/ directories"
mkdir -p "$VENDOR_DIR"
mkdir -p "$MODELS_DIR/mimicmotion"
mkdir -p "$MODELS_DIR/rife"
mkdir -p "$MODELS_DIR/dwpose"
mkdir -p "$MODELS_DIR/svd"

# ---------- clone MimicMotion repository ----------

echo ""
info "--- Cloning MimicMotion repository ---"
if [ -d "$VENDOR_DIR/MimicMotion" ]; then
    warn "vendor/MimicMotion already exists, pulling latest"
    cd "$VENDOR_DIR/MimicMotion"
    git pull
else
    git clone https://github.com/Tencent/MimicMotion.git "$VENDOR_DIR/MimicMotion"
fi
ok "MimicMotion repository ready"

# ---------- download model weights ----------

download_hf_model() {
    local repo_id="$1"
    local target_dir="$2"
    local label="$3"

    echo ""
    info "--- Downloading $label ---"
    info "Source: https://huggingface.co/$repo_id"

    if [ "$HAS_HF_CLI" = true ]; then
        huggingface-cli download "$repo_id" --local-dir "$target_dir" --local-dir-use-symlinks False
    else
        # Fallback: use wget to clone the HF repo via git LFS
        if [ -d "$target_dir/.git" ]; then
            warn "Directory $target_dir already contains a git repo, skipping"
        else
            GIT_LFS_SKIP_SMUDGE=0 git clone "https://huggingface.co/$repo_id" "$target_dir"
        fi
    fi
    ok "$label downloaded"
}

# 1. Stable Video Diffusion base model (~10 GB)
download_hf_model \
    "stabilityai/stable-video-diffusion-img2vid-xt" \
    "$MODELS_DIR/svd" \
    "SVD Base Model (stabilityai/stable-video-diffusion-img2vid-xt)"

# 2. MimicMotion weights (~2 GB)
download_hf_model \
    "tencent/MimicMotion" \
    "$MODELS_DIR/mimicmotion" \
    "MimicMotion Weights (tencent/MimicMotion)"

# 3. DWPose weights (~400 MB)
echo ""
info "--- Downloading DWPose weights ---"
DWPOSE_DIR="$MODELS_DIR/dwpose"
DWPOSE_DET_URL="https://huggingface.co/yzd-v/DWPose/resolve/main/yolox_l.onnx"
DWPOSE_POSE_URL="https://huggingface.co/yzd-v/DWPose/resolve/main/dw-ll_ucoco_384.onnx"

if [ ! -f "$DWPOSE_DIR/yolox_l.onnx" ]; then
    if [ "$HAS_HF_CLI" = true ]; then
        huggingface-cli download yzd-v/DWPose yolox_l.onnx --local-dir "$DWPOSE_DIR"
        huggingface-cli download yzd-v/DWPose dw-ll_ucoco_384.onnx --local-dir "$DWPOSE_DIR"
    else
        wget --progress=bar:force -O "$DWPOSE_DIR/yolox_l.onnx" "$DWPOSE_DET_URL"
        wget --progress=bar:force -O "$DWPOSE_DIR/dw-ll_ucoco_384.onnx" "$DWPOSE_POSE_URL"
    fi
    ok "DWPose weights downloaded"
else
    warn "DWPose weights already present, skipping"
fi

# 4. RIFE interpolation model (~100 MB)
echo ""
info "--- Downloading RIFE model weights ---"
RIFE_DIR="$MODELS_DIR/rife"
RIFE_URL="https://huggingface.co/AlexWortworworkerr/RIFE/resolve/main/flownet.pkl"

if [ ! -f "$RIFE_DIR/flownet.pkl" ]; then
    if [ "$HAS_HF_CLI" = true ]; then
        huggingface-cli download AlexWortworker/RIFE flownet.pkl --local-dir "$RIFE_DIR" 2>/dev/null || {
            warn "RIFE HuggingFace download failed, trying alternative source"
            # Alternative: download from practical-rife releases
            RIFE_ALT_URL="https://github.com/hzwer/Practical-RIFE/raw/main/train_log/flownet.pkl"
            wget --progress=bar:force -O "$RIFE_DIR/flownet.pkl" "$RIFE_ALT_URL" 2>/dev/null || {
                warn "RIFE download failed. You may need to download manually."
                warn "Place flownet.pkl in: $RIFE_DIR/"
            }
        }
    else
        RIFE_ALT_URL="https://github.com/hzwer/Practical-RIFE/raw/main/train_log/flownet.pkl"
        wget --progress=bar:force -O "$RIFE_DIR/flownet.pkl" "$RIFE_ALT_URL" 2>/dev/null || {
            warn "RIFE download failed. You may need to download manually."
            warn "Place flownet.pkl in: $RIFE_DIR/"
        }
    fi
    ok "RIFE model downloaded"
else
    warn "RIFE model already present, skipping"
fi

# ---------- verify CUDA availability ----------

echo ""
info "--- Verifying CUDA availability ---"

PYTHON_CMD="python3"
if [ -f "$ROOT_DIR/worker/.venv/bin/python" ]; then
    PYTHON_CMD="$ROOT_DIR/worker/.venv/bin/python"
fi

$PYTHON_CMD -c "
import torch
if torch.cuda.is_available():
    gpu_name = torch.cuda.get_device_name(0)
    vram_mb = torch.cuda.get_device_properties(0).total_mem / (1024**2)
    print(f'CUDA available: {gpu_name}')
    print(f'VRAM: {vram_mb:.0f} MB ({vram_mb/1024:.1f} GB)')
    if vram_mb < 12000:
        print('WARNING: MimicMotion recommends >= 12 GB VRAM for best results')
    print(f'CUDA version: {torch.version.cuda}')
    print(f'PyTorch version: {torch.__version__}')
else:
    print('WARNING: CUDA is NOT available.')
    print('MimicMotion requires an NVIDIA GPU with CUDA support.')
    print('Install PyTorch with CUDA: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124')
" 2>/dev/null || {
    warn "Could not verify CUDA (PyTorch may not be installed yet)"
    warn "Install PyTorch with CUDA support in the worker venv:"
    echo "       cd worker && .venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124"
}

# ---------- print GPU info via nvidia-smi ----------

echo ""
if command -v nvidia-smi &>/dev/null; then
    info "GPU Information:"
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits | \
        while IFS=, read -r name mem driver; do
            echo "       GPU: $name"
            echo "       VRAM: ${mem} MiB"
            echo "       Driver: $driver"
        done
else
    warn "nvidia-smi not found. Cannot display GPU details."
fi

# ---------- done ----------

echo ""
echo "====================================="
echo -e "  ${GREEN}MimicMotion setup complete!${NC}"
echo "====================================="
echo ""
echo "Model locations:"
echo "  SVD base:       $MODELS_DIR/svd/"
echo "  MimicMotion:    $MODELS_DIR/mimicmotion/"
echo "  DWPose:         $MODELS_DIR/dwpose/"
echo "  RIFE:           $MODELS_DIR/rife/"
echo "  MimicMotion repo: $VENDOR_DIR/MimicMotion/"
echo ""
echo "Update .env to use local generation:"
echo "  GENERATION_BACKEND=local"
echo "  MIMICMOTION_MODEL_DIR=./models/mimicmotion"
echo "  MIMICMOTION_REPO_DIR=./vendor/MimicMotion"
echo ""
