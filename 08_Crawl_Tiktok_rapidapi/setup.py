from setuptools import setup, find_packages

setup(
    name="tiktok2download",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'pandas',
        'requests',
        'python-dotenv',
        'openpyxl'
    ],
    python_requires='>=3.6',
) 