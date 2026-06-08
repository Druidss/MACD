#!/usr/bin/env bash
#
# BTC 6 小时定时分析 —— cron 包装脚本
#
# 每 6 小时运行一次，更新数据库并生成 6h 综合分析报告。
# 报告写入 data/analysis_reports/<时间戳>_6h_combined.md
# 运行日志写入 data/analysis_reports/cron_6h.log
#
# 安装到 crontab（每 6 小时整点运行：0/6/12/18 时）：
#   crontab -e
#   0 */6 * * * /path/to/repo/.claude/skills/btc-6h-scheduled/scripts/cron_6h.sh
#
# 手动测试：
#   bash .claude/skills/btc-6h-scheduled/scripts/cron_6h.sh

set -euo pipefail

# 解析脚本所在目录 → 仓库根目录（脚本位于 <repo>/.claude/skills/btc-6h-scheduled/scripts/）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

PYTHON="${PYTHON:-python3}"
LOG_DIR="${REPO_ROOT}/data/analysis_reports"
LOG_FILE="${LOG_DIR}/cron_6h.log"

mkdir -p "${LOG_DIR}"

{
  echo "=================================================="
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始 BTC 6h 定时分析"
  cd "${REPO_ROOT}"
  "${PYTHON}" "${SCRIPT_DIR}/run_6h_analysis.py" --timeframes 1d,12h,6h,4h
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 完成"
} >> "${LOG_FILE}" 2>&1
