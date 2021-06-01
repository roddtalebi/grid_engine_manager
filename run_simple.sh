#!/bin/bash
echo "is this thing on?"
# sleep_time=$(((RANDOM%181)))
sleep_time=7 # "$1"
output_file="simple_test.txt" #"$2"

sleep $sleep_time
echo "$sleep_time" >> $output_file