from setuptools import setup, find_packages

setup(
    name='rpi-arduino-pin',
    version='0.2.1',
    author='Taehun Kim',
    author_email='kimheuu0218@gmail.com',
    description='A Python library for controlling Raspberry Pi GPIO, I2C, SPI and communicating with Arduino via serial.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/SKARCH218/pin', # 본인의 GitHub 저장소 URL로 변경해주세요.
    packages=find_packages(),
    install_requires=[
        'lgpio',
        'pyserial',
        'pyserial-asyncio',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License', # LICENSE 파일에 따라 변경될 수 있습니다.
        'Operating System :: POSIX :: Linux', # 라즈베리파이 환경에 특화
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Embedded Systems',
        'Topic :: Home Automation',
    ],
    python_requires='>=3.6',
)
