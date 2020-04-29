import setuptools

with open('README.md', 'r') as f:
    long_desc = f.read()

setuptools.setup(
    name='aphro-AndreVallestero',
    version='0.0.1',
    author='Andre Vallestero',
    Description='HTTP proxy manager, rotator, and racer',
    long_description=long_desc,
    long_description_content_type='text/markdown',
    url='https://github.com/AndreVallestero/aphro',
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: AGPL-3.0 License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)