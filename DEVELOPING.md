Set up an virtual environment and set up develop mode:
```shell
python -m venv venv
. venv/bin/activate
pip install twine
python setup.py develop
```

Build:
```shell
python setup.py bdist
```

Run tests:
```shell
python setup.py test
```

Publishing:

- Create `.pypirc`. See https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/#create-an-account
- Then:
```shell
rm -rf dist
python setup.py sdist
twine upload dist/*
```
