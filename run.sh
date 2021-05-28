#!/bin/bash
# sleep_time=$(((RANDOM%181)))
sleep_time="$1"
output_file="$2"

sleep $sleep_time
echo "$sleep_time" >> $output_file