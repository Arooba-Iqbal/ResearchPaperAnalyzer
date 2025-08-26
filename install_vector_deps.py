#!/usr/bin/env python3
"""
Installation script for Vector Embeddings dependencies.
"""
import subprocess
import sys
import os


def install_package(package):
    """Install a package using pip."""
    try:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False


def check_package(package):
    """Check if a package is already installed."""
    try:
        __import__(package)
        return True
    except ImportError:
        return False


def main():
    """Main installation function."""
    print("=" * 60)
    print("Vector Embeddings Dependencies Installation")
    print("=" * 60)
    
    # List of required packages
    packages = [
        "sentence-transformers>=2.2.0",
        "numpy>=1.24.0", 
        "scikit-learn>=1.3.0",
        "faiss-cpu>=1.7.0"
    ]
    
    print("This script will install the following packages:")
    for package in packages:
        print(f"  - {package}")
    
    print("\nChecking existing installations...")
    
    # Check existing packages
    existing = []
    missing = []
    
    for package in packages:
        package_name = package.split(">=")[0].split("==")[0]
        if check_package(package_name):
            existing.append(package)
            print(f"✅ {package_name} already installed")
        else:
            missing.append(package)
            print(f"❌ {package_name} not found")
    
    if not missing:
        print("\n🎉 All packages are already installed!")
        return
    
    print(f"\nInstalling {len(missing)} missing packages...")
    
    # Install missing packages
    success_count = 0
    for package in missing:
        if install_package(package):
            success_count += 1
    
    print("\n" + "=" * 60)
    print("Installation Summary:")
    print(f"Total packages: {len(packages)}")
    print(f"Already installed: {len(existing)}")
    print(f"Successfully installed: {success_count}")
    print(f"Failed: {len(missing) - success_count}")
    
    if success_count == len(missing):
        print("\n🎉 All packages installed successfully!")
        print("\nNext steps:")
        print("1. Create a .env file based on env.example")
        print("2. Run: python manage.py rebuild_embeddings")
        print("3. Test with: python test_vector_rag.py")
    else:
        print("\n⚠️  Some packages failed to install.")
        print("Please check the error messages above and try again.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
