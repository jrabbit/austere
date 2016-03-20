from setuptools import setup
setup(
    name='austere',
    version='0.1.0',
    author='Jack Laxson',
    author_email='jackjrabbit+austere@gmail.com',
    url='https://github.com/jrabbit/austere',
    license='GPL v3',
    # long_description="",
    description="a default browser switcher based on material conditions & contexts",
    data_files=[('share/applications', ['austere.desktop'])],
    scripts=['austere.py'],
    # entry_points = {
    #     'console_scripts': ['austere=austere.command_line:main'],
    # }
    install_requires=["clint==0.5.1", "psutil==4.0.0"],
    classifiers=['Environment :: X11 Applications',
                 'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
                 'Topic :: Internet :: WWW/HTTP :: Browsers',
                 'Topic :: Multimedia', 'Operating System :: POSIX :: Linux', 
                 'Programming Language :: Python :: 3.5',
                 'Programming Language :: Python :: 2.7', ]
)
