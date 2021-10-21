
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from pathlib import Path

# Define the directory that setup.py is in
here = Path(__file__).parent.resolve()

# Define the directory with our extra files
volian_dir = here / 'volian'
data_dir = volian_dir / 'files'

# Make our list of files to include 
files = []
# Get every file recursively that is in the ./volian/files directory
for file in data_dir.rglob('*'):
	files.append(str(file.relative_to(volian_dir)))
# Append any extra files with path relative to volian
files.append('Mirrors.masterlist')
# Get the long description from the README file
long_description = (here / 'README.md').read_text(encoding='utf-8')

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
    name='volian',  # Required
    version='1.0.0.dev1',  # Required
    description='An installer for Debian or Ubuntu',  # Optional
    long_description=long_description,  # Optional
    long_description_content_type='text/markdown',  # Optional (see note above)
    url='https://github.com/volitank/volian',  # Optional
    author='Blake Lee',  # Optional
    author_email='blake@volitank.com',  # Optional
    classifiers=[  # Optional
	# List of classifiers https://gist.github.com/nazrulworld/3800c84e28dc464b2b30cec8bc1287fc
        'Development Status :: 1 - Planning',
		'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
		'Natural Language :: English',
		'Operating System :: POSIX :: Linux',
		'Topic :: System :: Installation/Setup',
		'Topic :: System :: Operating System Kernels :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
    ],

    keywords='debian, installer, ubuntu',  # Optional
	#package_dir={'': 'src'}, # Optional
    packages=['volian'],  # Required
    python_requires='>=3.6, <4',

    package_data={  # Optional
		'volian': files,
    },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/distutils/setupscript.html#installing-additional-files
    #
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[('my_data', ['data/data_file'])],  # Optional

    entry_points={  # Optional
        'console_scripts': [
            'volian=volian.__main__:main',
        ],
    },

    project_urls={  # Optional
        'Source': 'https://github.com/volitank/volian',
    },
)
