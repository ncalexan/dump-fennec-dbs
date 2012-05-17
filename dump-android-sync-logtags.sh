#!/bin/sh

TAGS=`grep -ir "LOG_TAG =" * | sed -e "s/.*= \"//" -e "s/\".*//"`
for tag in TAGS; do adb shell setprop log.tag.$tag VERBOSE; done
