ethcrt
####################

The original project used to develop this repo can be found here
`stacker <https://github.com/cloudtools/stacker#stacker>`_ project

Requirements
============

* Python 3.4+
* `aws-vault https://github.com/99designs/aws-vault`
* `poetry <https://poetry.eustace.io/>`_

Usage
=====

1. Clone this repo
2. Run `make setup`
3. Modify the environment files accordingly
4. Run `stacker build --profile <profile> --stacks stacker-bucket stacker.yaml`
   
Note: You should try to make your ``stacker_bucket`` variable unique
since S3 bucket names share a global namespace. It will default to
``stacker-ethcrt`` but you may choose any unique value.

Project tree
=================

In this example we have a product called ``ethcrt`` and two environments
called ``dev`` and ``prod``.

Some notes about the files in this tree:

**conf/<env>.env**:
 This is an "environment" file which holds variables that change in the config
 based on the environment. This allows you to have a single config for all
 your environments, while changing small things per environment.

 See: http://stacker.readthedocs.io/en/latest/environments.html

**stacker.yaml**:
 This is a "stacker config" file.

 See: http://stacker.readthedocs.io/en/latest/config.html

**blueprints/touch.py**:
 This is a tiny ``stacker blueprint`` that doesn't do much of anything.
 A blueprint is used to programatically generate CloudFormation JSON.

 See: http://stacker.readthedocs.io/en/latest/blueprints.html

**tests/blueprints/test_touch.py**:
  This is a tiny ``stacker blueprint`` test which only creates a simple
  resource in CloudFormation (a WaitCondition, which does nothing on it's own).

  See: http://stacker.readthedocs.io/en/latest/blueprints.html#testing-blueprints

Running a release
====================

In this example we use a ``Makefile`` to save commands.  The commands will be
ran using **poetry** which will handle creating a virtualenv for you, as well
as insuring that the correct packages are installed.

To execute stacker using your dev environment, using the *--interactive* flag
run::

 make dev ARGS=--interactive

To execute stacker using the prod environment, run::

 make prod ARGS=--interactive
