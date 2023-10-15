# simple Makefile for some common tasks
.PHONY: clean test dist release pypi tagv

paste-version := $(shell python setup.py --version)

clean:
	find . -name "*.pyc" |xargs rm || true
	rm -r dist || true
	rm -r build || true
	rm -rf .tox || true
	rm -r cover .coverage || true
	rm -r .eggs || true
	rm -r paste.egg-info || true

tagv:
	git tag -s -m ${paste-version} ${paste-version}
	git push origin master --tags

cleanagain:
	find . -name "*.pyc" |xargs rm || true
	rm -r dist || true
	rm -r build || true
	rm -r .tox || true
	rm -r cover .coverage || true
	rm -r .eggs || true
	rm -r paste.egg-info || true

test:
	tox --skip-missing-interpreters

dist: test
	python3 setup.py sdist bdist_wheel

release: clean test cleanagain tagv pypi gh

pypi:
	python3 setup.py sdist bdist_wheel
	twine upload dist/*

gh:
	gh release create ${paste-version} --generate-notes dist/*
