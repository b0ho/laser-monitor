from setuptools import setup, find_packages

setup(
    name="laser-monitor",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'Flask>=2.0.0',
        'opencv-python-headless>=4.7.0',
        'numpy>=1.21.0',
        'Pillow>=9.0.0',
        'python-dotenv>=0.19.0',
        'ultralytics>=8.0.0'
    ],
    python_requires='>=3.8',
)