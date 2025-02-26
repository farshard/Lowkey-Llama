"""Tests for hardware compatibility checks."""

import pytest
import yaml
from pathlib import Path

class ModelCompatibilityTest:
    """Test hardware compatibility for different models."""
    
    def setup_method(self):
        """Set up test environment."""
        self.models_dir = Path(__file__).parent.parent / "models"
        self.gpu_info = self._get_gpu_info()

    def _get_gpu_info(self):
        """Get GPU information if available."""
        try:
            import torch
            if torch.cuda.is_available():
                return {
                    "name": torch.cuda.get_device_name(0),
                    "memory": torch.cuda.get_device_properties(0).total_memory,
                    "compute_capability": torch.cuda.get_device_capability(0)
                }
        except ImportError:
            pass
        return None

    def load_model_config(self, model_file: str):
        """Load model configuration from YAML."""
        with open(self.models_dir / model_file) as f:
            return yaml.safe_load(f)

    def get_recommended_profile(self, config):
        """Get recommended profile based on hardware."""
        if not self.gpu_info:
            return "cpu"
        
        gpu_memory = self.gpu_info["memory"] / (1024**3)  # Convert to GB
        
        if gpu_memory >= config["performance"]["memory_requirements"]["recommended_vram_gb"]:
            return "high"
        elif gpu_memory >= config["performance"]["memory_requirements"]["minimum_vram_gb"]:
            return "medium"
        else:
            return "cpu"

    def test_mistral_compatibility(self):
        """Test Mistral model compatibility."""
        config = self.load_model_config('mistral.yaml')
        profile = self.get_recommended_profile(config)

        # Check minimum requirements
        min_req = config["performance"]["memory_requirements"]["minimum_vram_gb"]
        assert isinstance(min_req, (int, float))
        assert min_req > 0

        # Check recommended requirements
        rec_req = config["performance"]["memory_requirements"]["recommended_vram_gb"]
        assert isinstance(rec_req, (int, float))
        assert rec_req >= min_req

    def test_codellama_compatibility(self):
        """Test CodeLlama model compatibility."""
        config = self.load_model_config('codellama.yaml')
        profile = self.get_recommended_profile(config)

        # Check optimization settings
        assert "optimization" in config
        assert "quantization" in config["optimization"]
        assert isinstance(config["optimization"]["quantization"]["supported_types"], list)

        # Check tensor parallelism
        assert "tensor_parallelism" in config["optimization"]
        assert isinstance(config["optimization"]["tensor_parallelism"]["min_gpus"], int)
        assert isinstance(config["optimization"]["tensor_parallelism"]["max_gpus"], int)

    def test_performance_profiles(self):
        """Test performance profile configurations."""
        for model_file in ['mistral.yaml', 'codellama.yaml']:
            config = self.load_model_config(model_file)
            
            # Check performance metrics
            assert "performance" in config
            assert "max_batch_size" in config["performance"]
            assert "max_sequence_length" in config["performance"]
            assert "throughput" in config["performance"]

            # Validate memory requirements
            mem_req = config["performance"]["memory_requirements"]
            assert "minimum_vram_gb" in mem_req
            assert "recommended_vram_gb" in mem_req
            assert mem_req["recommended_vram_gb"] >= mem_req["minimum_vram_gb"]

    def test_adaptive_layer_split(self):
        """Test adaptive layer splitting configuration."""
        if not self.gpu_info:
            pytest.skip("No GPU available")

        for model_file in ['mistral.yaml', 'codellama.yaml']:
            config = self.load_model_config(model_file)
            profile = self.get_recommended_profile(config)

            # Check optimization settings
            assert "optimization" in config
            assert "tensor_parallelism" in config["optimization"]
            tp_config = config["optimization"]["tensor_parallelism"]
            
            # Verify tensor parallelism settings
            assert tp_config["supported"] in [True, False]
            if tp_config["supported"]:
                assert isinstance(tp_config["min_gpus"], int)
                assert isinstance(tp_config["max_gpus"], int)
                assert tp_config["max_gpus"] >= tp_config["min_gpus"] 