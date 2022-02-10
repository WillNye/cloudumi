#!/bin/bash

echo "Executing create_pkg.sh..."
if [[ -d $output_path ]]; then
  rm -rf $output_path
fi

mkdir -p $output_path

find $source_path -iname "*.py" -exec cp {} $output_path \;
pip install -r $source_path/requirements.txt -t $output_path