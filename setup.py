from setuptools import setup, find_packages
import sys
import subprocess
from typing import List

def validate_dependencies() -> None:
    """Cross-platform dependency checks with better error messages"""
    requirements = [
        ('python', '3.8', '--version', "https://www.python.org/downloads/"),
        ('ollama', None, '--version', "https://ollama.ai/download"),
        ('git', None, '--version', "https://git-scm.com/downloads")
    ]
    
    missing = []
    for name, min_version, version_flag, help_url in requirements:
        try:
            result = subprocess.run(
                [name, version_flag],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            if min_version and not any(v in result.stdout for v in min_version.split(',')):
                missing.append(f"{name} >= {min_version} (install from {help_url})")
        except (FileNotFoundError, PermissionError):
            missing.append(f"{name} (install from {help_url})")
    
    if missing:
        sys.exit(f"Missing critical dependencies:\n- " + "\n- ".join(missing))

def install_packages(requirements: List[str]) -> bool:
    """Install Python packages with retry logic"""
    retries = 3
    for attempt in range(retries):
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-U'] + requirements)
            return True
        except subprocess.CalledProcessError:
            if attempt == retries - 1:
                return False

if __name__ == "__main__":
    validate_dependencies()
    
    base_reqs = [
        'fastapi', 'pydantic', 'aiohttp', 'httpx', 
        'streamlit', 'uvicorn', 'psutil', 'python-dotenv'
    ]
    
    if not install_packages(base_reqs):
        sys.exit("Failed to install Python dependencies")

    setup(
        name="local-llm",
        version="0.1.0",
        packages=find_packages(),
        install_requires=base_reqs,
        extras_require={
            'test': ['pytest', 'pytest-asyncio', 'pytest-cov'],
            'dev': ['mypy', 'types-requests', 'types-psutil']
        },
        entry_points={
            'console_scripts': [
                'local-llm=src.core.launcher:main',
                'llm-diag=src.diagnostics:run_checks'
            ]
        }
    ) 