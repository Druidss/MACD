# Codex Routine：BTC 6h Binance 动能报告

如果 Codex 产品侧提供 Routine / Scheduled task，可以用下面这份任务定义。

## Routine 名称

BTC 6h Binance 动能报告

## 运行频率

每 6 小时一次，尽量设置在 Binance 6h K 线收盘后 3-5 分钟：

- `00:05 UTC`
- `06:05 UTC`
- `12:05 UTC`
- `18:05 UTC`

如果 Routine UI 只支持自然语言，就填：

```text
每 6 小时运行一次，在 UTC 00:05、06:05、12:05、18:05 附近运行。
```

## Routine Prompt

```text
使用当前 MACD 项目，生成 BTC 6h Binance 动能报告。

要求：
1. 使用 Binance futures BTCUSDT 的已收盘 K 线，不要使用正在形成的 K 线。
2. 如果可访问仓库，请运行：
   python3 scripts/binance_momentum_report.py \
     --market futures \
     --symbol BTCUSDT \
     --timeframes 1d,12h,6h,4h,2h,1h,30m \
     --limit 720 \
     --report-style u2-compact \
     --output data/analysis_reports/latest_binance_6h_momentum.md
3. 如果当前 Routine 环境无法访问仓库或无法运行脚本，则使用 $binance 连接器获取 1d、12h、6h、4h、2h、1h、30m K线，按项目口径计算/复核 EMA26、EMA52、MACD(12,26,9)，并参考 `.agents/skills/btc-momentum-analyzer/THEORY.md` 的 Unit1/Unit2 与 EMA52 触及规则生成同结构极简报告。
4. 报告必须包含：
   - 只列出已经进入 U2 的时间级别，不列“将形成 U2”，不局限于 6h
   - 一句话概括这些 U2 时间级别与 1d 的同向或矛盾关系
   - 一句话给出做单进场点；如果 U2 与 1d 矛盾，则明确暂无进场点
5. 输出用中文，固定覆盖 `data/analysis_reports/latest_binance_6h_momentum.md`，最后明确说明本报告不构成投资建议。
```

## 成功标准

- Routine 每次运行都能产出一份 Markdown 风格中文报告。
- 报告只列出已经进入 U2 的时间级别。
- 报告必须包含 U2 级别与 1d 的关系，以及做单进场点。
- 每次运行覆盖同一个文件：`data/analysis_reports/latest_binance_6h_momentum.md`。

## 注意

当前已创建 Codex automation：`btc-6h-binance`。

为避免每次运行创建新的报告对话，任务应固定覆盖
`data/analysis_reports/latest_binance_6h_momentum.md`，对话里只保留一行更新状态。
