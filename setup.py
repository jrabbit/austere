from setuptools import setup
setup(
    name='austere',
    version='0.1a1',
    author='Jack Laxson',
    author_email='jackjrabbit+austere@gmail.com',
    url='https://github.com/jrabbit/austere',
    license='GPL v3',
    # long_description="",
    description="a default browser switcher based on material conditions & contexts",
    scripts=['austere.py'],
    install_requires=['psutil'],
    classifiers=['Environment :: X11 Applications',
                 'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
                 'Topic :: Internet :: WWW/HTTP :: Browsers',
                 'Topic :: Multimedia', ]
)
