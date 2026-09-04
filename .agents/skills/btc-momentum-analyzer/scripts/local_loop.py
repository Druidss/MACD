#!/usr/bin/env python3
"""
BTC 数据本地抓取循环

在用户本地机器上运行，定期从 OKX 获取最新 BTC K 线数据，
更新 data/database/btc_database.json，并可选自动 git push。

容器（Claude Code on the Web）因网络策略无法访问 OKX API，
需要本地运行此脚本来保持数据库最新，容器只负责读取和分析。

使用方法:
  # 前台运行，每 6 小时更新一次（默认）
  python3 local_loop.py

  # 自定义间隔（分钟）
  python3 local_loop.py --interval 60

  # 仅运行一次后退出
  python3 local_loop.py --once

  # 更新后自动 git commit & push
  python3 local_loop.py --git-push

  # 指定要更新的时间级别
  python3 local_loop.py --timeframes 1d,12h,6h,4h

  # 初始化数据库（首次使用）
  python3 local_loop.py --init
"""

import os
import sys
import time
import argparse
import subprocess
from datetime import datetime

# 确保可以导入同目录下的模块
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)

from database_manager import BTCDatabase, ALL_TIMEFRAMES

# 默认配置
DEFAULT_INTERVAL_MINUTES = 360  # 6 小时
DEFAULT_TIMEFRAMES = ["1d", "12h", "6h", "4h"]

# 项目根目录（脚本在 .claude/skills/btc-momentum-analyzer/scripts/ 下）
PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", "..", ".."))


def git_commit_and_push(message: str = None):
    """执行 git add + commit + push"""
    if message is None:
        message = f"chore: update btc database {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    try:
        db_path = os.path.join(PROJECT_ROOT, "data", "database", "btc_database.json")

        # git add 只提交数据库文件，不提交其他变更
        subprocess.run(
            ["git", "add", db_path],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
        )

        # 检查是否有东西需要提交
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=PROJECT_ROOT,
            capture_output=True,
        )
        if result.returncode == 0:
            print("[INFO] 数据库无变化，跳过 git commit", flush=True)
            return True

        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "push"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
        )

        print(f"[GIT] 已推送：{message}", flush=True)
        return True

    except subprocess.CalledProcessError as e:
        print(f"[GIT ERROR] {e.stderr.decode() if e.stderr else e}", flush=True)
        return False


def run_once(db: BTCDatabase, timeframes: list, git_push: bool = False):
    """执行一次数据更新"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*50}", flush=True)
    print(f"[{now}] 开始更新数据库...", flush=True)
    print(f"时间级别: {', '.join(timeframes)}", flush=True)

    try:
        database = db.update_database(timeframes)

        if database:
            # 打印各时间级别最新状态
            print("\n最新数据状态:", flush=True)
            for tf in timeframes:
                if tf in database["timeframes"]:
                    tf_data = database["timeframes"][tf]
                    last = tf_data["candles"][-1]
                    dif = last.get("dif")
                    dea = last.get("dea")
                    hist = last.get("histogram")
                    print(
                        f"  {tf:5s}  close={last['close']:>10.2f}  "
                        f"DIF={dif:>8.1f}  DEA={dea:>8.1f}  Hist={hist:>8.1f}  [{last['datetime']}]"
                        if dif is not None else
                        f"  {tf:5s}  close={last['close']:>10.2f}  [指标未计算]  [{last['datetime']}]",
                        flush=True,
                    )

            if git_push:
                git_commit_and_push()

            print(f"[{now}] 更新完成", flush=True)
            return True
        else:
            print(f"[ERROR] 更新失败", flush=True)
            return False

    except Exception as e:
        print(f"[ERROR] 异常: {e}", flush=True)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="BTC 数据本地抓取循环（在本地机器运行，容器读取数据库做分析）"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_MINUTES,
        help=f"更新间隔（分钟，默认 {DEFAULT_INTERVAL_MINUTES} = 6小时）",
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="只运行一次后退出",
    )

    parser.add_argument(
        "--init",
        action="store_true",
        help="初始化数据库（首次使用时运行）",
    )

    parser.add_argument(
        "--timeframes",
        type=str,
        default=",".join(DEFAULT_TIMEFRAMES),
        help=f"要更新的时间级别（逗号分隔，默认: {','.join(DEFAULT_TIMEFRAMES)}）",
    )

    parser.add_argument(
        "--git-push",
        action="store_true",
        help="每次更新后自动 git commit & push（容器会 git pull 拿到最新数据）",
    )

    parser.add_argument(
        "--all-timeframes",
        action="store_true",
        help="更新所有 8 个时间级别（2d/1d/12h/6h/4h/2h/1h/30m）",
    )

    args = parser.parse_args()

    # 解析时间级别
    if args.all_timeframes:
        timeframes = ALL_TIMEFRAMES
    else:
        timeframes = [tf.strip() for tf in args.timeframes.split(",")]

    print(f"BTC 数据本地抓取循环", flush=True)
    print(f"项目根目录: {PROJECT_ROOT}", flush=True)
    print(f"时间级别: {', '.join(timeframes)}", flush=True)
    if not args.once:
        print(f"更新间隔: 每 {args.interval} 分钟（{args.interval/60:.1f} 小时）", flush=True)
    if args.git_push:
        print(f"Git Push: 开启", flush=True)

    db = BTCDatabase()

    # 初始化模式
    if args.init:
        print("\n[INIT] 初始化数据库...", flush=True)
        db.initialize_database(timeframes)
        if args.git_push:
            git_commit_and_push("chore: init btc database")
        print("[INIT] 完成", flush=True)
        return

    # 检查数据库是否已初始化
    status = db.get_status()
    if status["status"] == "not_initialized":
        print("\n[ERROR] 数据库未初始化，请先运行：", flush=True)
        print(f"  python3 {__file__} --init", flush=True)
        sys.exit(1)

    # 单次运行模式
    if args.once:
        success = run_once(db, timeframes, args.git_push)
        sys.exit(0 if success else 1)

    # 循环模式
    print(f"\n开始循环（Ctrl+C 退出）...", flush=True)

    # 立即执行一次
    run_once(db, timeframes, args.git_push)

    while True:
        next_run = datetime.now().timestamp() + args.interval * 60
        next_str = datetime.fromtimestamp(next_run).strftime("%H:%M:%S")
        print(f"\n下次更新: {next_str}（{args.interval} 分钟后）", flush=True)

        try:
            time.sleep(args.interval * 60)
        except KeyboardInterrupt:
            print("\n[INFO] 已停止", flush=True)
            break

        run_once(db, timeframes, args.git_push)


if __name__ == "__main__":
    main()
