# coding=utf8

from setuptools import setup

setup(name="DDDProxy",
	version="4.0.0",
	description="DDDProxy",
	author="wdongxv@gmail.com",
	url="https://github.com/wdongxv/DDDProxy",
	license="",
	packages=["DDDProxy"],
	install_requires=[
		"pycrypto==2.6.1"
    ],
	scripts=[
        '/install.py'
    ]
)
