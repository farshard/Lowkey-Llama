import unittest
import os
import yaml
import psutil
import GPUtil
from pathlib import Path

class HardwareInfo:
    @staticmethod
    def get_gpu_info():
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                return {
                    'name': gpus[0].name,
                    'vram_total': gpus[0].memoryTotal / 1024,  # GB
                    'vram_free': gpus[0].memoryFree / 1024,    # GB
                    'vram_used': gpus[0].memoryUsed / 1024     # GB
                }
            return None
        except:
            return None

    @staticmethod
    def get_cpu_info():
        return {
            'threads': psutil.cpu_count(logical=True),
            'cores': psutil.cpu_count(logical=False),
            'ram_total': psutil.virtual_memory().total / (1024**3),  # GB
            'ram_available': psutil.virtual_memory().available / (1024**3)  # GB
        }

class ModelCompatibilityTest(unittest.TestCase):
    def setUp(self):
        self.models_dir = Path("models")
        self.hw_info = HardwareInfo()
        self.gpu_info = self.hw_info.get_gpu_info()
        self.cpu_info = self.hw_info.get_cpu_info()

    def load_model_config(self, model_file):
        with open(self.models_dir / model_file) as f:
            return yaml.safe_load(f)

    def get_recommended_profile(self, model_config):
        if not self.gpu_info:
            return 'cpu_only'
        
        vram_available = self.gpu_info['vram_free']
        if vram_available >= 8:
            return 'high_vram'
        elif vram_available >= 6:
            return 'medium_vram'
        elif vram_available >= 4:
            return 'low_vram'
        return 'cpu_only'

    def test_mistral_compatibility(self):
        config = self.load_model_config('mistral.yaml')
        profile = self.get_recommended_profile(config)
        
        # Check minimum requirements
        min_req = config['hardware_requirements']['minimum']
        self.assertGreaterEqual(
            self.cpu_info['ram_total'],
            min_req['ram'],
            "Insufficient RAM for Mistral"
        )
        self.assertGreaterEqual(
            self.cpu_info['threads'],
            min_req['cpu_threads'],
            "Insufficient CPU threads for Mistral"
        )
        
        # Test profile selection
        layer_config = config['gpu_configuration']['layer_configurations'][profile]
        self.assertIsNotNone(layer_config, "No valid configuration found for hardware")

    def test_codellama_compatibility(self):
        config = self.load_model_config('codellama.yaml')
        profile = self.get_recommended_profile(config)
        
        for variant in config['variants']:
            with self.subTest(variant=variant['name']):
                if self.gpu_info:
                    vram_required = variant['vram_required']
                    can_run = self.gpu_info['vram_total'] >= vram_required
                    if not can_run:
                        print(f"Warning: {variant['name']} requires {vram_required}GB VRAM")
                        print(f"Available: {self.gpu_info['vram_total']}GB")
                        print(f"Recommended profile: {variant['default_profile']}")
                        print("Consider using CPU offloading or a smaller model")

    def test_performance_profiles(self):
        for model_file in ['mistral.yaml', 'codellama.yaml']:
            config = self.load_model_config(model_file)
            profiles = config['performance_profiles']
            
            with self.subTest(model=model_file):
                # Test balanced profile
                balanced = profiles['balanced']
                self.assertLessEqual(
                    balanced['batch_size'],
                    8,
                    f"Batch size too large for {model_file}"
                )
                
                # Test memory efficient profile
                memory = profiles['memory_efficient']
                self.assertLessEqual(
                    memory['batch_size'],
                    balanced['batch_size'],
                    f"Memory efficient profile should have smaller batch size"
                )

    def test_adaptive_layer_split(self):
        if not self.gpu_info:
            self.skipTest("No GPU available")
        
        for model_file in ['mistral.yaml', 'codellama.yaml']:
            config = self.load_model_config(model_file)
            profile = self.get_recommended_profile(config)
            
            with self.subTest(model=model_file):
                layer_config = config['gpu_configuration']['layer_configurations'][profile]
                self.assertIn('gpu_layers', layer_config)
                self.assertIn('cpu_layers', layer_config)
                
                if profile != 'high_vram':
                    self.assertLess(
                        layer_config['gpu_layers'],
                        config['gpu_configuration']['default_gpu_layers'],
                        f"GPU layers not properly reduced for {profile}"
                    )

if __name__ == '__main__':
    unittest.main() 