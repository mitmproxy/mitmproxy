#!/bin/bash

chmod +x java/gradlew

publishingReplacement="$(cat publishing.overlay.build.gradle)"
publishingReplacementEscaped=$(echo "$publishingReplacement" | sed 's/[\^$.*/&]/\\&/g')

buildGradle="$(cat java/build.gradle)"
newBuildGradle=`echo -e "$buildGradle" | perl -0777 -pe "s/(?<=publishing )(\{(?:[^{}]+|(?1))*\})/$publishingReplacementEscaped/gs"`

echo "$newBuildGradle" > java/build.gradle


