""" Entry points for cryptomate deployments """

import argparse
import sys


def parse_arguments(args=None):
    ''' Convert command-line arguments into usable options '''
    parser = argparse.ArgumentParser()
    return parser.parse_args(args)


def main(args=None):
    ''' Entry point, installed as cli command '''
    options = parse_arguments(args=args)
    return 0
