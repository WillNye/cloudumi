#!/bin/bash

function exit_if_terraform_is_missing {
    terraform > /dev/null
    if [[ $? == 127 ]]; then
        return 0
    else
        echo "Terraform is missing, install it pls"
        exit 1
    fi
}

function setup_tf_workspaces {
    for live_config_folder_path in $(find live -maxdepth 2 -type d)
    do
        live_config_folder=${live_config_folder_path#"live/"}
        if [[ "$live_config_folder" == *\/* ]]
        then
            workspace="${live_config_folder//\//-}"
            echo "Setting up staging and production workspaces for $workspace"
            terraform workspace new $workspace
        fi
    done
}

# Exit if terraform is missing
exit_if_terraform_is_missing

# Setup terraform workspaces
setup_tf_workspaces