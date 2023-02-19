from setuptools import setup, find_packages
setup(
    name='PSNLib',
    version='0.0.1',
    packages=find_packages(),
    package_data={
        'PSNLib': ['assets/PSNOCR', 'assets/*.png'],
    },
    include_package_data=True,
)