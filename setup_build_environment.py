#!/usr/bin/env python3
"""
Build environment setup script for portable executable packaging.
Installs PyInstaller and validates the build environment.
"""

import sys
import subprocess
import os
from pathlib import Path
from build_utils import BuildEnvironmentValidator, DependencyDetector, install_missing_dependencies


def install_pyinstaller():
    """Install PyInstaller if not already installed."""
    try:
        import PyInstaller
        print(f"✓ PyInstaller already installed (version {PyInstaller.__version__})")
        return True
    except ImportError:
        print("Installing PyInstaller...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], 
                         check=True, capture_output=True, text=True)
            import PyInstaller
            print(f"✓ PyInstaller installed successfully (version {PyInstaller.__version__})")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install PyInstaller: {e}")
            return False
        except ImportError:
            print("✗ PyInstaller installation failed - import error")
            return False


def install_build_dependencies():
    """Install additional build dependencies."""
    dependencies = [
        'hypothesis',  # For property-based testing
        'pytest',     # For running tests
    ]
    
    missing = []
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✓ {dep} already installed")
        except ImportError:
            missing.append(dep)
    
    if missing:
        print(f"Installing missing dependencies: {', '.join(missing)}")
        return install_missing_dependencies(missing)
    
    return True


def validate_project_structure():
    """Validate that the project has the required structure for packaging."""
    required_files = [
        'run_app.py',           # Main application entry point
        'requirements.txt',     # Dependencies
        'work_tools/settings.py', # Django settings
        'db.sqlite3',          # Database file
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("✗ Missing required files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    print("✓ All required project files present")
    return True


def create_virtual_environment():
    """Create a virtual environment for isolated packaging."""
    venv_path = Path("venv_packaging")
    
    if venv_path.exists():
        print("✓ Virtual environment already exists")
        return True
    
    try:
        print("Creating virtual environment for packaging...")
        subprocess.run([sys.executable, '-m', 'venv', str(venv_path)], 
                      check=True, capture_output=True, text=True)
        print("✓ Virtual environment created successfully")
        
        # Provide instructions for activation
        if os.name == 'nt':  # Windows
            activate_script = venv_path / "Scripts" / "activate.bat"
            print(f"To activate: {activate_script}")
        else:  # Unix-like
            activate_script = venv_path / "bin" / "activate"
            print(f"To activate: source {activate_script}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create virtual environment: {e}")
        return False


def main():
    """Main setup function."""
    print("=" * 60)
    print("Build Environment Setup for Portable EXE Packaging")
    print("=" * 60)
    print()
    
    success = True
    
    # Step 1: Validate project structure
    print("Step 1: Validating project structure...")
    if not validate_project_structure():
        success = False
    print()
    
    # Step 2: Install PyInstaller
    print("Step 2: Installing PyInstaller...")
    if not install_pyinstaller():
        success = False
    print()
    
    # Step 3: Install build dependencies
    print("Step 3: Installing build dependencies...")
    if not install_build_dependencies():
        success = False
    print()
    
    # Step 4: Validate build environment
    print("Step 4: Validating build environment...")
    validator = BuildEnvironmentValidator()
    validation_result = validator.validate_all()
    
    if validation_result['overall_valid']:
        print("✓ Build environment validation passed")
    else:
        print("✗ Build environment validation failed")
        success = False
        
        # Print detailed issues
        for check_name, check_result in validation_result['checks'].items():
            if isinstance(check_result, dict):
                if not check_result.get('valid', True):
                    print(f"  Issue in {check_name}: {check_result.get('message', 'Unknown error')}")
                if 'issues' in check_result:
                    for issue in check_result['issues']:
                        print(f"  - {issue}")
    print()
    
    # Step 5: Verify dependency detection
    print("Step 5: Verifying dependency detection...")
    detector = DependencyDetector()
    
    # Check requirements parsing
    requirements = detector.get_requirements_from_file()
    print(f"✓ Detected {len(requirements)} requirements from requirements.txt")
    
    # Check missing dependencies
    missing = detector.detect_missing_dependencies()
    if missing:
        print(f"⚠ Missing dependencies: {', '.join(missing)}")
        print("  Consider installing them with: pip install " + " ".join(missing))
    else:
        print("✓ All required dependencies are installed")
    
    # Check hidden imports
    hidden_imports = detector.get_hidden_imports()
    print(f"✓ Generated {len(hidden_imports)} hidden imports for PyInstaller")
    print()
    
    # Step 6: Create virtual environment (optional)
    print("Step 6: Creating virtual environment (optional)...")
    create_virtual_environment()
    print()
    
    # Summary
    print("=" * 60)
    if success:
        print("✓ Build environment setup completed successfully!")
        print()
        print("Next steps:")
        print("1. Run tests: python -m pytest tests/ -v")
        print("2. Build package: python build.bat")
        print("3. Test package: python test_package.bat")
    else:
        print("✗ Build environment setup failed!")
        print("Please resolve the issues above before proceeding.")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)