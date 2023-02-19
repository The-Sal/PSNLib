from setuptools import setup, find_packages
setup(
    name='PSNLib',
    version='0.0.1',
    packages=find_packages(),
    package_data={
        'PSNLib': ['assets/PSNOCR', 'assets/*.png'],
    },
    include_package_data=True,
    # The following are dependencies that are required for this package to work.
    install_requires=[
        'Vis @ git+https://github.com/The-Sal/DartVision.git'
    ]
)