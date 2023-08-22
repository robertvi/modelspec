#!/bin/bash

#
# delete any existing virtual environment folder
# create a new virtual environment
# install modelspec inside it
# modelspec should already be git cloned 
#

set -eu

#set any project related environment variables
source ./includes

rm -rf ./${VIRTENV_NAME}
python3 -m venv ./${VIRTENV_NAME}
source ./${VIRTENV_NAME}/bin/activate

pip install ${REQUIRED_PIP_PACKAGES}
cd ${MODELSPEC_PATH}
pip install .
