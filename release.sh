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

new_minor=$((minor+1))
new_version="v$major.$new_minor.0"

#echo "branch_name = $branch_name"
#echo "working_version = $working_version"
#echo "major = $major"
#echo "minor = $minor"
#echo "patch = $patch"

# So far, I can do only minor release
if [ ${patch} != "0" ]; then
  echo 'ERROR! Not minor release.'
  exit 2
fi

# TODO check combination
# make summary and ask user for confirmation
echo "You are going to release from branch '$branch_name' version '$version'."
echo "New version will be called '$new_version'."
echo "Do you want to proceed? [Y/n]"
read answer

if [[ ${answer} != 'y' && ${answer} != 'Y' && -n ${answer} ]]; then
  echo 'Stopped by user.'
  exit 2
fi

# create branch for release
git fetch
# !!!!!!!!!!!!!!!!!!!!!!!!!+
#git checkout -b "releasing-$version"

cur_date_time=$(date --utc +"%Y-%m-%d %TZ")
cur_date=$(date --utc +"%Y-%m-%d")

# update version.txt
echo $version > version.txt
# put date of release into CHANGELOG.md
echo $cur_date_time >> version.txt

sed -i "s/{release-date}/$cur_date/" CHANGELOG.md

# creates release commit, tag it, push it
git add version.txt
git add CHANGELOG.md
git commit -m "Release $version"
git tag -a $version -m "Release $version"

# update version.txt
cur_date_time=$(date --utc +"%Y-%m-%d %TZ")
echo "$new_version-dev" > version.txt
echo $cur_date_time >> version.txt

# update CHANGELOG.md (add structure for next version)
changelog_template="# Changelog\n\n## $new_version\n  {release-date}\n### Upgrade requirements\n### Migrations\n### Changes/"
echo "changelog_template = $changelog_template"
sed -i "s/^# Changelog/$changelog_template" CHANGELOG.md

# commit with next version
git add version.txt
git add CHANGELOG.md
git commit -m "Setup $new_version"

# in case of minor release, create brach X.Y.x
# create pull request
#
# checkout X.Y.x
# update version.txt
# update CHANGELOG.md (add structure for next version)
# commit with next version
# push

#git push --tags
#git push
