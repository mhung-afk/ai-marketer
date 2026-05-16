#!/usr/bin/env python3
"""
AWS CDK Application Entry Point

This module initializes and synthesizes the Healing Bedroom infrastructure stack.
"""

import os
import subprocess
from aws_cdk import App, Environment
from cdk.stack import HealingBedroomStack

# Sync Lambda layer files before CDK synthesis
subprocess.run(
    ["bash", "scripts/sync-layer.sh"],
    cwd=os.path.dirname(__file__),
    check=True
)

# Initialize CDK App
app = App()

# Get AWS region and account from context or environment
region = app.node.try_get_context("region") or os.getenv("AWS_REGION", "us-east-1")
account = app.node.try_get_context("account") or os.getenv("AWS_ACCOUNT_ID")

# Environment configuration
env = Environment(
    account=account,
    region=region,
)

# Create the main infrastructure stack
healing_bedroom_stack = HealingBedroomStack(
    app,
    "HealingBedroomStackCDK",
    env=env,
    description="Healing Bedroom MVP - Phase 1 AWS Infrastructure Foundation"
)

# Synthesize CloudFormation template
app.synth()
