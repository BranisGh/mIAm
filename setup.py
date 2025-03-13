import setuptools

# Read the contents of the README.md file for the long description
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# Read the contents of the requirements.md file for installation
with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f]

# Define package metadata
VERSION = "0.0.0"  # Package version
AUTHOR_USER_NAME = "Branis Ghoul"
AUTHOR_EMAIL = "branisghoul02@hotmail.com"

# Package configuration using setuptools
setuptools.setup(
    name="mIAm",  
    version=VERSION,  
    author=AUTHOR_USER_NAME, 
    author_email=AUTHOR_EMAIL,  
    description="mIAm is a powerful tool for culinary assistance.", 
    long_description=long_description, 
    long_description_content_type="text/markdown", 
    package_dir={"": "src"},  
    packages=setuptools.find_packages(where="src"),  
    
    # Added dependencies from requirements.txt
    install_requires=requirements
)