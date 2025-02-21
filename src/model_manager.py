import os
import shutil
import subprocess
from pathlib import Path
import yaml
import psutil
import GPUtil

class ModelManager:
    def __init__(self):
        # Storage paths
        self.ssd_path = Path("C:/local-llm/models/active")
        self.hdd_path = Path("E:/ollama_models")
        self.default_ollama_path = Path(os.path.expanduser("~/.ollama/models"))
        self.cache_dir = Path("C:/local-llm/models/active/cache")
        
        # VRAM constraints
        self.gpu = self.get_gpu_info()
        self.vram_limit = 8  # GB for RTX 3070
        
        # Model VRAM requirements (in GB)
        self.model_vram = {
            'mistral': 4,
            'codellama:13b-q4': 5,
            'codellama:34b-q4': 8,
            'mixtral:8x7b-q4': 12,
            'llama2:70b-q4': 19
        }
        
        # Create directories if they don't exist
        for path in [self.ssd_path, self.hdd_path, self.cache_dir]:
            path.mkdir(parents=True, exist_ok=True)

    def get_gpu_info(self):
        """Get GPU information"""
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                return gpus[0]  # First GPU
            return None
        except:
            return None

    def check_vram_availability(self, required_vram):
        """Check if there's enough VRAM available"""
        if not self.gpu:
            return False
        
        available_vram = self.gpu.memoryFree / 1024  # Convert to GB
        return available_vram >= required_vram

    def get_drive_usage(self, path):
        """Get drive usage information"""
        usage = psutil.disk_usage(str(path.drive))
        return {
            'total': usage.total / (1024**3),  # GB
            'used': usage.used / (1024**3),
            'free': usage.free / (1024**3),
            'percent': usage.percent
        }

    def move_model_to_ssd(self, model_name):
        """Move a model from HDD to SSD for active use"""
        # Check VRAM requirements
        vram_needed = self.model_vram.get(model_name, 4)  # Default to 4GB if unknown
        if vram_needed > self.vram_limit:
            print(f"Warning: {model_name} requires {vram_needed}GB VRAM, but only {self.vram_limit}GB available")
            print("Consider using a smaller model or reducing GPU layers")
            return

        source = self.hdd_path / model_name
        target = self.ssd_path / model_name
        
        # Check if there's enough space
        ssd_usage = self.get_drive_usage(self.ssd_path)
        if source.exists() and source.stat().st_size / (1024**3) < ssd_usage['free']:
            print(f"Moving {model_name} to SSD for faster access...")
            shutil.move(str(source), str(target))
            print(f"Model {model_name} is now on SSD")
            
            # Suggest optimal GPU layers
            if vram_needed > 6:  # For models requiring >6GB VRAM
                print(f"Recommended GPU layers setting for {model_name}: 28")
                print("Add to .env: OLLAMA_GPU_LAYERS=28")
        else:
            print(f"Error: Not enough space on SSD or model not found")

    def move_model_to_hdd(self, model_name):
        """Move a model from SSD to HDD for storage"""
        source = self.ssd_path / model_name
        target = self.hdd_path / model_name
        
        # Check if there's enough space
        hdd_usage = self.get_drive_usage(self.hdd_path)
        if source.exists() and source.stat().st_size / (1024**3) < hdd_usage['free']:
            print(f"Moving {model_name} to HDD for storage...")
            shutil.move(str(source), str(target))
            print(f"Model {model_name} is now on HDD")
        else:
            print(f"Error: Not enough space on HDD or model not found")

    def list_models(self):
        """List all models and their locations with storage and VRAM information"""
        print("\nGPU Status:")
        if self.gpu:
            print(f"  GPU: {self.gpu.name}")
            print(f"  Total VRAM: {self.gpu.memoryTotal/1024:.1f}GB")
            print(f"  Used VRAM: {self.gpu.memoryUsed/1024:.1f}GB")
            print(f"  Free VRAM: {self.gpu.memoryFree/1024:.1f}GB")
        else:
            print("  No GPU detected")

        print("\nStorage Status:")
        for drive, path in [("SSD (Active)", self.ssd_path), ("HDD (Storage)", self.hdd_path)]:
            usage = self.get_drive_usage(path)
            print(f"\n{drive}:")
            print(f"  Total: {usage['total']:.2f} GB")
            print(f"  Used: {usage['used']:.2f} GB ({usage['percent']}%)")
            print(f"  Free: {usage['free']:.2f} GB")
            print("\n  Models:")
            
            total_model_size = 0
            for model in path.glob("*"):
                if model.is_file() and not model.name.startswith('.'):
                    size = model.stat().st_size / (1024**3)  # Size in GB
                    vram_req = self.model_vram.get(model.name, "unknown")
                    total_model_size += size
                    print(f"    - {model.name} ({size:.2f} GB, VRAM: {vram_req}GB)")
            print(f"\n  Total model size: {total_model_size:.2f} GB")

    def optimize_storage(self):
        """Optimize model storage based on VRAM and storage space"""
        print("\nOptimizing storage allocation...")
        
        # Define model categories based on VRAM requirements
        active_models = {
            'mistral': 4,  # VRAM in GB
            'codellama:13b-q4': 5
        }
        
        archive_models = {
            'codellama:34b-q4': 8
        }
        
        # Check SSD space
        ssd_usage = self.get_drive_usage(self.ssd_path)
        required_ssd_space = sum(active_models.values()) + 5  # Additional 5GB for cache
        
        if ssd_usage['free'] < required_ssd_space:
            print(f"Warning: Not enough space on SSD for active models")
            print(f"Required: {required_ssd_space:.2f} GB, Available: {ssd_usage['free']:.2f} GB")
            return
        
        # Move active models to SSD if they fit VRAM constraints
        for model, vram in active_models.items():
            if vram <= self.vram_limit:
                self.move_model_to_ssd(model)
            else:
                print(f"Warning: {model} requires {vram}GB VRAM, skipping...")
        
        # Move archive models to HDD
        for model in archive_models:
            self.move_model_to_hdd(model)

def main():
    manager = ModelManager()
    print("Current Model Storage Status:")
    manager.list_models()
    
    print("\nOptimizing model storage...")
    manager.optimize_storage()
    
    print("\nUpdated Model Storage Status:")
    manager.list_models()

if __name__ == "__main__":
    main() 