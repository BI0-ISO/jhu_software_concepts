from setuptools import find_packages, setup


setup(
    name="gradcafe-module-5",
    version="0.1.0",
    description="Flask dashboard + ETL pipeline for GradCafe analytics (Module 5).",
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    install_requires=[
        "Flask",
        "psycopg",
        "beautifulsoup4",
        "urllib3",
        "certifi",
        "huggingface_hub",
        "llama-cpp-python",
    ],
    python_requires=">=3.10",
)
