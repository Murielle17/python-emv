from setuptools import setup, find_packages
from codecs import open
from os import path

# Obtenez le chemin absolu du répertoire actuel
here = path.abspath(path.dirname(__file__))

# Lire le fichier README.md pour la description longue
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

# Lire la version depuis "__init__.py" dans le dossier emv
version = {}
with open(path.join(here, "emv", "__init__.py"), encoding="utf-8") as fp:
    exec(fp.read(), version)

# Configuration du package
setup(
    name="emv.MurielleM",  # Nom de votre package
    version=version["__version__"],  # Version extraite de __init__.py
    description="EMV Smartcard Protocol Library",  # Description courte
    long_description=long_description,  # Description longue
    long_description_content_type="text/markdown",  # Type de contenu pour la description longue
    license="MIT",  # Licence
    author="Russ Garrett",  # Auteur
    author_email="russ@garrett.co.uk",  # Email de l'auteur
    url="https://github.com/russss/python-emv",  # URL du projet
    classifiers=[  # Liste des classificateurs pour PyPI
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    keywords="smartcard emv payment",  # Mots-clés
    python_requires=">=3.4",  # Version minimale de Python requise
    packages=find_packages(where="."),  # Inclut automatiquement tous les sous-packages
    install_requires=[  # Dépendances principales
        "pyscard==2.0.0",
        "pycountry==20.7.3",
        "terminaltables==3.1.0",
        "click==7.1.2",
    ],
    entry_points={  # Scripts de console
        "console_scripts": [
            "emvtool=emv.command.client:run",  # Exemple de commande console
        ],
    },
)
