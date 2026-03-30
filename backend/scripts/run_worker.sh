#!/usr/bin/env bash
set -euo pipefail

dramatiq app.workers.tasks
