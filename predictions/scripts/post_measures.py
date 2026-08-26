#!/usr/bin/env python3
"""
CLI for publishing fake measurements into an environment:

    python scripts/post_measures.py --help

Thin on purpose: the arguments, the generators and the two routes (queue batch vs
direct POST to the IoT Agent) are documented in
crowd_predictions/fake_measures.py, which is where they live.
"""

from crowd_predictions.fake_measures import main

if __name__ == "__main__":
    main()
