import setuptools,os

with open("README.md", "r") as fh:
    long_description = fh.read()

lib_folder = os.path.dirname(os.path.realpath(__file__))
requirement_path = lib_folder + '/requirements.txt'
install_requires = []
if os.path.isfile(requirement_path):
    with open(requirement_path) as f:
        install_requires = f.read().splitlines()

setuptools.setup(
     name='blockchainbay',  
     install_requires=install_requires,
     version='1.5',
     scripts=['blockChainBay.py'] ,
     author="Alfredo Ortega",
     author_email="ortegaalfredo@gmail.com",
     description="The Blockchainbay is a torrent distribution tool hosted on a EVM-compatible blockchain.",
     long_description=long_description,
     long_description_content_type="text/markdown",
     url="https://github.com/ortegaalfredo/blockchainbay",
     packages=setuptools.find_packages(),
     classifiers=[
         "Programming Language :: Python :: 3",
         "License :: OSI Approved :: BSD License",
         "Operating System :: OS Independent",
     ],
 )
