# ==============================================================================
# Dance Coaching Platform - MimicMotion GPU Model Setup (Windows PowerShell)
# ==============================================================================
# Downloads and configures MimicMotion for local GPU-based video generation.
# Requires: git, python with CUDA-capable PyTorch, ~15 GB disk space.
#
# Run from the repository root:
#     powershell -ExecutionPolicy Bypass -File scripts\setup-mimicmotion.ps1
# ==============================================================================

$ErrorActionPreference = "Stop"

$RootDir   = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VendorDir = Join-Path $RootDir "vendor"
$ModelsDir = Join-Path $RootDir "models"

function Write-Ok($msg)   { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Fail($msg)  { Write-Host "[FAIL]  $msg" -ForegroundColor Red }
function Write-Info($msg)  { Write-Host "[INFO]  $msg" -ForegroundColor Cyan }

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  MimicMotion GPU Setup"
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "WARNING: This will download approximately 15 GB of model weights." -ForegroundColor Yellow
Write-Host "Make sure you have sufficient disk space and a stable connection." -ForegroundColor Yellow
Write-Host ""

$confirm = Read-Host "Continue? [y/N]"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Aborted."
    exit 0
}
Write-Host ""

# ---------- check prerequisites ----------

try {
    $null = Get-Command git -ErrorAction Stop
    Write-Ok "git found"
} catch {
    Write-Fail "git is required but not found"
    Write-Host "       Install from https://git-scm.com/download/win"
    exit 1
}

$HasHfCli = $false
try {
    $null = Get-Command huggingface-cli -ErrorAction Stop
    $HasHfCli = $true
    Write-Ok "huggingface-cli found"
} catch {
    Write-Warn "huggingface-cli not found, will use git clone for HuggingFace models"
    Write-Host "       Optional install: pip install huggingface_hub[cli]"
}

# ---------- create directories ----------

Write-Info "Creating vendor\ and models\ directories"
$dirs = @(
    $VendorDir,
    "$ModelsDir\mimicmotion",
    "$ModelsDir\rife",
    "$ModelsDir\dwpose",
    "$ModelsDir\svd"
)
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# ---------- clone MimicMotion repository ----------

Write-Host ""
Write-Info "--- Cloning MimicMotion repository ---"
$mimicDir = Join-Path $VendorDir "MimicMotion"
if (Test-Path $mimicDir) {
    Write-Warn "vendor\MimicMotion already exists, pulling latest"
    Push-Location $mimicDir
    git pull
    Pop-Location
} else {
    git clone https://github.com/Tencent/MimicMotion.git $mimicDir
}
Write-Ok "MimicMotion repository ready"

# ---------- download helpers ----------

function Download-HFModel {
    param(
        [string]$RepoId,
        [string]$TargetDir,
        [string]$Label
    )

    Write-Host ""
    Write-Info "--- Downloading $Label ---"
    Write-Info "Source: https://huggingface.co/$RepoId"

    if ($HasHfCli) {
        huggingface-cli download $RepoId --local-dir $TargetDir --local-dir-use-symlinks False
    } else {
        if (Test-Path "$TargetDir\.git") {
            Write-Warn "Directory $TargetDir already contains a git repo, skipping"
        } else {
            $env:GIT_LFS_SKIP_SMUDGE = "0"
            git clone "https://huggingface.co/$RepoId" $TargetDir
            Remove-Item Env:\GIT_LFS_SKIP_SMUDGE -ErrorAction SilentlyContinue
        }
    }
    Write-Ok "$Label downloaded"
}

function Download-File {
    param(
        [string]$Url,
        [string]$OutPath,
        [string]$Label
    )

    if (Test-Path $OutPath) {
        Write-Warn "$Label already present, skipping"
        return
    }

    Write-Info "Downloading $Label..."
    try {
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $Url -OutFile $OutPath -UseBasicParsing
        $ProgressPreference = 'Continue'
        Write-Ok "$Label downloaded"
    } catch {
        Write-Warn "Download failed for $Label. You may need to download manually."
        Write-Host "       URL: $Url"
        Write-Host "       Target: $OutPath"
    }
}

# ---------- download model weights ----------

# 1. SVD base model (~10 GB)
Download-HFModel `
    -RepoId "stabilityai/stable-video-diffusion-img2vid-xt" `
    -TargetDir "$ModelsDir\svd" `
    -Label "SVD Base Model (stabilityai/stable-video-diffusion-img2vid-xt)"

# 2. MimicMotion weights (~2 GB)
Download-HFModel `
    -RepoId "tencent/MimicMotion" `
    -TargetDir "$ModelsDir\mimicmotion" `
    -Label "MimicMotion Weights (tencent/MimicMotion)"

# 3. DWPose weights (~400 MB)
Write-Host ""
Write-Info "--- Downloading DWPose weights ---"
$dwposeDir = "$ModelsDir\dwpose"

if ($HasHfCli) {
    huggingface-cli download yzd-v/DWPose yolox_l.onnx --local-dir $dwposeDir 2>$null
    huggingface-cli download yzd-v/DWPose dw-ll_ucoco_384.onnx --local-dir $dwposeDir 2>$null
    Write-Ok "DWPose weights downloaded"
} else {
    Download-File `
        -Url "https://huggingface.co/yzd-v/DWPose/resolve/main/yolox_l.onnx" `
        -OutPath "$dwposeDir\yolox_l.onnx" `
        -Label "DWPose detector (yolox_l.onnx)"
    Download-File `
        -Url "https://huggingface.co/yzd-v/DWPose/resolve/main/dw-ll_ucoco_384.onnx" `
        -OutPath "$dwposeDir\dw-ll_ucoco_384.onnx" `
        -Label "DWPose pose estimator (dw-ll_ucoco_384.onnx)"
}

# 4. RIFE interpolation model (~100 MB)
Write-Host ""
Write-Info "--- Downloading RIFE model weights ---"
$rifeDir = "$ModelsDir\rife"
Download-File `
    -Url "https://github.com/hzwer/Practical-RIFE/raw/main/train_log/flownet.pkl" `
    -OutPath "$rifeDir\flownet.pkl" `
    -Label "RIFE model (flownet.pkl)"

# ---------- verify CUDA availability ----------

Write-Host ""
Write-Info "--- Verifying CUDA availability ---"

$pythonCmd = "python"
$venvPython = "$RootDir\worker\.venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonCmd = $venvPython
}

try {
    & $pythonCmd -c @"
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
    print('Install PyTorch with CUDA:')
    print('  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124')
"@
} catch {
    Write-Warn "Could not verify CUDA (PyTorch may not be installed yet)"
    Write-Host "       Install PyTorch with CUDA support in the worker venv:"
    Write-Host "       cd worker && .venv\Scripts\pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124"
}

# ---------- print GPU info via nvidia-smi ----------

Write-Host ""
try {
    $null = Get-Command nvidia-smi -ErrorAction Stop
    Write-Info "GPU Information:"
    $gpuInfo = nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits
    $gpuInfo | ForEach-Object {
        $parts = $_ -split ','
        Write-Host "       GPU: $($parts[0].Trim())"
        Write-Host "       VRAM: $($parts[1].Trim()) MiB"
        Write-Host "       Driver: $($parts[2].Trim())"
    }
} catch {
    Write-Warn "nvidia-smi not found. Cannot display GPU details."
}

# ---------- done ----------

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  MimicMotion setup complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Model locations:"
Write-Host "  SVD base:         $ModelsDir\svd\"
Write-Host "  MimicMotion:      $ModelsDir\mimicmotion\"
Write-Host "  DWPose:           $ModelsDir\dwpose\"
Write-Host "  RIFE:             $ModelsDir\rife\"
Write-Host "  MimicMotion repo: $VendorDir\MimicMotion\"
Write-Host ""
Write-Host "Update .env to use local generation:"
Write-Host "  GENERATION_BACKEND=local"
Write-Host "  MIMICMOTION_MODEL_DIR=./models/mimicmotion"
Write-Host "  MIMICMOTION_REPO_DIR=./vendor/MimicMotion"
Write-Host ""
