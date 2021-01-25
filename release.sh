#!/bin/bash

set -e
#set -x
# get current branch from git
branch_name=$(git symbolic-ref -q HEAD)
branch_name=${branch_name##refs/heads/}
branch_name=${branch_name:-HEAD}

# get current version from version.txt
working_version=''
while IFS= read -r line || [[ -n "$line" ]]; do
  if [[ -z "$working_version" ]]
  then
    working_version="$line"
  fi
done < version.txt

is_dev=${working_version#*-}
if [ ${is_dev} != dev ]; then
  echo 'ERROR! Not development version.'
  exit 2
fi

version=${working_version%%-*}
major_with=${working_version%%.*}
major=${major_with#v}
major_rest=${working_version#*.}
minor=${major_rest%%.*}
minor_rest=${major_rest#*.}
patch=${minor_rest%%-*}

echo "branch_name = $branch_name"
echo "working_version = $working_version"
echo "major = $major"
echo "minor = $minor"
echo "patch = $patch"

# TODO check combination
# make summary and ask user for confirmation
echo "You are going to release from branch '$branch_name' version '$version'. Do you want to proceed? [Y]"
read answer

if [[ ${answer} != 'y' && ${answer} != 'Y' && -n ${answer} ]]; then
  echo 'Stopped by user.'
  exit 2
fi

# create branch for release
#git checkout -b "Release $version"

cur_date_time=$(date +"%Y-%m-%d %T")
cur_date=$(date +"%Y-%m-%d")

# update version.txt
echo $version > version.txt
echo $cur_date_time >> version.txt

# put date of release into CHANGELOG.md


# creates release commit, tag it, push it
# in case of minor release, create brach X.Y.x
# update version.txt
# update CHANGELOG.md (add structure for next version)
# commit with next version
# create pull request
#
# checkout X.Y.x
# update version.txt
# update CHANGELOG.md (add structure for next version)
# commit with next version
# push
