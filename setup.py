from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="tution_center",
    version="15.0.0",
    description="Advanced Tuition Centre Management App for Frappe Framework v15+",
    author="Joshent",
    author_email="joshent31@gmail.com",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    long_description=long_description,
)
