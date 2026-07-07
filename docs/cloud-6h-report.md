# BTC 6h Binance 云端报告

这个项目现在有两条 6h 自动报告路径：

1. **GitHub Actions 托管定时任务**：不需要 VPS，仓库启用 Actions 后每 6h 自动跑。
2. **VPS / Docker / systemd timer**：适合你想把报告长期保存在自己的服务器上。

## 方案 A：GitHub Actions（推荐先用）

文件：`.github/workflows/btc-6h-binance-report.yml`

触发时间：

- `00:03 UTC`
- `06:03 UTC`
- `12:03 UTC`
- `18:03 UTC`

这些时间点比 Binance 6h K 线收盘晚 3 分钟，脚本默认只使用已收盘 K 线，避免把正在形成的 K 线算进去。

输出：

- GitHub Actions job summary 中展示报告前 80 行
- Artifact: `btc-6h-binance-momentum-report`
  - `latest_binance_6h_momentum.md`
  - `latest_binance_6h_momentum.json`
  - 当次带时间戳的 Markdown 报告

手动触发：

1. 打开 GitHub 仓库 `Actions`
2. 选择 `BTC 6h Binance Momentum Report`
3. 点击 `Run workflow`

### 同步分支到 GitHub

当前重构分支：

```bash
git push -u origin codex/binance-6h-cloud-report
```

如果 HTTPS remote 提示 `could not read Username for 'https://github.com'`，说明本机没有可用
GitHub 凭据。可以二选一：

1. 在本机登录 GitHub CLI 后再 push：

   ```bash
   gh auth login
   git push -u origin codex/binance-6h-cloud-report
   ```

2. 使用 SSH remote。若 22 端口被网络拦截，可用 GitHub SSH over 443：

   ```bash
   git -c core.sshCommand="ssh -p 443 -o StrictHostKeyChecking=accept-new" \
     push -u ssh://git@ssh.github.com/Druidss/MACD.git codex/binance-6h-cloud-report
   ```

如果这里报 `Permission denied (publickey)`，需要先把本机 SSH 公钥加入 GitHub 账号。

可选 Telegram 推送：

在 GitHub 仓库 `Settings -> Secrets and variables -> Actions` 添加：

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

存在这两个 secrets 时，workflow 会把报告摘要发到 Telegram。

## 方案 B：VPS / Docker / systemd timer

部署文件：

- `Dockerfile`
- `docker-compose.yml`
- `deploy/systemd/macd-binance-6h-report.service`
- `deploy/systemd/macd-binance-6h-report.timer`

假设仓库部署到 VPS 的 `/opt/macd`：

```bash
cd /opt/macd
docker compose build
sudo cp deploy/systemd/macd-binance-6h-report.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now macd-binance-6h-report.timer
systemctl list-timers macd-binance-6h-report.timer
```

手动跑一次：

```bash
cd /opt/macd
docker compose run --rm analyzer
```

报告会写到：

```text
data/analysis_reports/
```

## 本地核对命令

```bash
python3 scripts/binance_momentum_report.py \
  --market futures \
  --symbol BTCUSDT \
  --timeframes 1d,12h,6h,4h,2h,1h,30m \
  --stdout
```
