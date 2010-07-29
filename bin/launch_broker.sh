#!/bin/bash

DIR=$(cd $(dirname "$0"); pwd)
BIN=$DIR"/../bin"
ETC=$DIR"/../etc"

echo "Launching Broker (that export all data)"
$BIN/shinken-broker.py -d -c $ETC/brokerd.cfg