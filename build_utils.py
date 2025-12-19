"""
Build utilities for portable executable packaging.
Provides dependency detection and build environment validation.
"""

import os
import sys
import subprocess
import importlib
import pkg_resources
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DependencyDetector:
    """Detects and validates Python dependencies for packaging."""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.requirements_file = self.project_root / "requirements.txt"
        
    def get_installed_packages(self) -> Dict[str, str]:
        """Get all installed packages and their versions."""
        installed = {}
        try:
            for dist in pkg_resources.working_set:
                installed[dist.project_name.lower()] = dist.version
        except Exception as e:
            logger.error(f"Failed to get installed packages: {e}")
            # Fallback: try to import and check common packages
            try:
                import django
                installed['django'] = getattr(django, '__version__', 'unknown')
            except ImportError:
                pass
            try:
                import waitress
                installed['waitress'] = 'installed'  # waitress doesn't have __version__
            except ImportError:
                pass
            try:
                import openpyxl
                installed['openpyxl'] = getattr(openpyxl, '__version__', 'unknown')
            except ImportError:
                pass
            try:
                import pypinyin
                installed['pypinyin'] = 'installed'
            except ImportError:
                pass
        return installed
    
    def get_requirements_from_file(self) -> Dict[str, str]:
        """Parse requirements.txt and return package requirements."""
        requirements = {}
        if not self.requirements_file.exists():
            logger.warning(f"Requirements file not found: {self.requirements_file}")
            return requirements
            
        try:
            with open(self.requirements_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Parse package name and version
                        if '>=' in line:
                            name, version = line.split('>=', 1)
                        elif '==' in line:
                            name, version = line.split('==', 1)
                        elif '>' in line:
                            name, version = line.split('>', 1)
                        else:
                            name, version = line, None
                        
                        requirements[name.strip().lower()] = version.strip() if version else None
        except Exception as e:
            logger.error(f"Failed to parse requirements file: {e}")
            
        return requirements
    
    def detect_missing_dependencies(self) -> List[str]:
        """Detect missing dependencies from requirements.txt."""
        installed = self.get_installed_packages()
        required = self.get_requirements_from_file()
        
        missing = []
        for package, version in required.items():
            if package not in installed:
                missing.append(f"{package}{f'>={version}' if version else ''}")
                
        return missing
    
    def detect_project_modules(self) -> Set[str]:
        """Detect all Python modules in the project."""
        modules = set()
        
        # Scan for Python files
        for py_file in self.project_root.rglob("*.py"):
            if py_file.name == "__init__.py":
                # Get package name from directory
                rel_path = py_file.parent.relative_to(self.project_root)
                if str(rel_path) != ".":
                    modules.add(str(rel_path).replace(os.sep, "."))
            else:
                # Get module name from file
                rel_path = py_file.relative_to(self.project_root)
                module_path = str(rel_path.with_suffix("")).replace(os.sep, ".")
                modules.add(module_path)
                
        return modules
    
    def validate_pyinstaller_compatibility(self) -> Tuple[bool, List[str]]:
        """Validate that all dependencies are compatible with PyInstaller."""
        issues = []
        
        try:
            import PyInstaller
        except ImportError:
            issues.append("PyInstaller is not installed")
            return False, issues
            
        # Check for known problematic packages
        installed = self.get_installed_packages()
        problematic_packages = {
            'matplotlib': 'May require additional hooks for proper packaging',
            'numpy': 'Large package, consider excluding if not needed',
            'pandas': 'Large package, consider excluding if not needed',
            'scipy': 'Large package with native dependencies',
        }
        
        for package, warning in problematic_packages.items():
            if package in installed:
                issues.append(f"Warning: {package} - {warning}")
                
        return len([i for i in issues if not i.startswith("Warning:")]) == 0, issues
    
    def get_hidden_imports(self) -> List[str]:
        """Generate list of hidden imports for PyInstaller."""
        hidden_imports = []
        
        # Add Django-specific imports
        django_imports = [
            'django.contrib.staticfiles',
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.core.management',
            'django.core.management.commands',
            'django.db.backends.sqlite3',
        ]
        hidden_imports.extend(django_imports)
        
        # Add project modules
        project_modules = self.detect_project_modules()
        hidden_imports.extend(project_modules)
        
        # Add third-party dependencies
        third_party = ['waitress', 'pypinyin', 'argparse', 'openpyxl']
        hidden_imports.extend(third_party)
        
        return hidden_imports
    
    def validate_build_environment(self) -> Dict[str, any]:
        """Comprehensive build environment validation."""
        result = {
            'valid': True,
            'issues': [],
            'warnings': [],
            'dependencies': {
                'installed': self.get_installed_packages(),
                'required': self.get_requirements_from_file(),
                'missing': self.detect_missing_dependencies(),
            },
            'pyinstaller': {
                'available': False,
                'version': None,
                'compatible': False,
            },
            'project': {
                'modules': list(self.detect_project_modules()),
                'hidden_imports': self.get_hidden_imports(),
            }
        }
        
        # Check PyInstaller
        try:
            import PyInstaller
            result['pyinstaller']['available'] = True
            result['pyinstaller']['version'] = PyInstaller.__version__
            
            compatible, issues = self.validate_pyinstaller_compatibility()
            result['pyinstaller']['compatible'] = compatible
            result['issues'].extend([i for i in issues if not i.startswith("Warning:")])
            result['warnings'].extend([i for i in issues if i.startswith("Warning:")])
            
        except ImportError:
            result['valid'] = False
            result['issues'].append("PyInstaller is not installed")
            
        # Check missing dependencies
        if result['dependencies']['missing']:
            result['valid'] = False
            result['issues'].extend([f"Missing dependency: {dep}" for dep in result['dependencies']['missing']])
            
        return result


class BuildEnvironmentValidator:
    """Validates the build environment for packaging."""
    
    def __init__(self):
        self.detector = DependencyDetector()
        
    def check_python_version(self) -> Tuple[bool, str]:
        """Check if Python version is suitable for packaging."""
        version = sys.version_info
        if version.major == 3 and version.minor >= 8:
            return True, f"Python {version.major}.{version.minor}.{version.micro}"
        else:
            return False, f"Python {version.major}.{version.minor}.{version.micro} (requires 3.8+)"
            
    def check_disk_space(self, required_mb: int = 500) -> Tuple[bool, str]:
        """Check available disk space."""
        try:
            import shutil
            free_bytes = shutil.disk_usage('.').free
            free_mb = free_bytes / (1024 * 1024)
            
            if free_mb >= required_mb:
                return True, f"{free_mb:.0f} MB available"
            else:
                return False, f"Only {free_mb:.0f} MB available (requires {required_mb} MB)"
        except Exception as e:
            return False, f"Could not check disk space: {e}"
            
    def validate_all(self) -> Dict[str, any]:
        """Run all validation checks."""
        result = {
            'overall_valid': True,
            'checks': {}
        }
        
        # Python version check
        python_ok, python_msg = self.check_python_version()
        result['checks']['python_version'] = {
            'valid': python_ok,
            'message': python_msg
        }
        if not python_ok:
            result['overall_valid'] = False
            
        # Disk space check
        disk_ok, disk_msg = self.check_disk_space()
        result['checks']['disk_space'] = {
            'valid': disk_ok,
            'message': disk_msg
        }
        if not disk_ok:
            result['overall_valid'] = False
            
        # Dependency validation
        dep_result = self.detector.validate_build_environment()
        result['checks']['dependencies'] = dep_result
        if not dep_result['valid']:
            result['overall_valid'] = False
            
        return result


def install_missing_dependencies(missing_deps: List[str]) -> bool:
    """Install missing dependencies using pip."""
    if not missing_deps:
        return True
        
    try:
        cmd = [sys.executable, '-m', 'pip', 'install'] + missing_deps
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Successfully installed: {', '.join(missing_deps)}")
            return True
        else:
            logger.error(f"Failed to install dependencies: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error installing dependencies: {e}")
        return False


if __name__ == "__main__":
    # Command line interface for testing
    validator = BuildEnvironmentValidator()
    result = validator.validate_all()
    
    print("Build Environment Validation Report")
    print("=" * 50)
    print(f"Overall Status: {'PASS' if result['overall_valid'] else 'FAIL'}")
    print()
    
    for check_name, check_result in result['checks'].items():
        print(f"{check_name.replace('_', ' ').title()}:")
        if isinstance(check_result, dict) and 'valid' in check_result:
            status = "PASS" if check_result['valid'] else "FAIL"
            print(f"  Status: {status}")
            if 'message' in check_result:
                print(f"  Details: {check_result['message']}")
        print()